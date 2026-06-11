# agents/supervisor.py
import asyncio
import logging
import os
from typing import TypedDict

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from agents.code_reviewer import CodeReviewerAgent
from agents.fetcher import fetch_pr_data
from agents.hitl import save_pending_review
from agents.poster import post_pr_comment
from agents.prompts import AGGREGATOR_PROMPT
from agents.security_agent import SecurityAgent
from agents.test_agent import TestAgent

logger = logging.getLogger(__name__)


class PRReviewState(TypedDict):
    repo: str
    pr_number: int
    pr_data: dict
    code_review: str
    security_review: str
    test_review: str
    final_report: str
    human_approved: bool
    human_action: str
    review_id: str
    error: str


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )


async def fetch_node(state: PRReviewState) -> dict:
    logger.info("Fetching PR data: %s#%s", state["repo"], state["pr_number"])
    try:
        pr_data = fetch_pr_data(state["repo"], state["pr_number"])
        return {"pr_data": pr_data}
    except Exception as e:
        logger.exception("Failed to fetch PR data")
        return {"error": str(e), "pr_data": {}}


async def review_node(state: PRReviewState) -> dict:
    if state.get("error"):
        return {
            "code_review": "Skipped — fetch failed.",
            "security_review": "Skipped — fetch failed.",
            "test_review": "Skipped — fetch failed.",
        }

    pr_data = state["pr_data"]
    llm = get_llm()

    code_agent = CodeReviewerAgent(llm)
    security_agent = SecurityAgent(llm)
    test_agent = TestAgent(llm)

    logger.info("Running 3 agents in parallel for PR #%s", state["pr_number"])

    code_review, security_review, test_review = await asyncio.gather(
        code_agent.review(pr_data),
        security_agent.review(pr_data),
        test_agent.review(pr_data),
    )

    return {
        "code_review": code_review,
        "security_review": security_review,
        "test_review": test_review,
    }


async def aggregate_node(state: PRReviewState) -> dict:
    if state.get("error"):
        return {
            "final_report": "Review could not be completed — PR fetch failed.",
            "human_approved": False,
        }

    logger.info("Aggregating reviews for PR #%s", state["pr_number"])
    llm = get_llm()
    prompt = AGGREGATOR_PROMPT.format(
        code_review=state["code_review"],
        security_review=state["security_review"],
        test_review=state["test_review"],
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        final_report = response.content
    except Exception:
        logger.exception("Aggregator LLM call failed")
        final_report = "\n\n".join([
            state["code_review"],
            state["security_review"],
            state["test_review"],
        ])

    return {"final_report": final_report, "human_approved": False}


async def hitl_node(state: PRReviewState) -> dict:
    """Pause graph — save state to Redis and wait for human decision."""
    if state.get("error"):
        return {"human_action": "reject", "review_id": ""}

    review_id = await save_pending_review(state)
    logger.info(
        "HITL checkpoint — review_id: %s — waiting for human approval at POST /review/%s/approve",
        review_id, review_id,
    )
    return {"review_id": review_id, "human_action": "pending"}


async def post_node(state: PRReviewState) -> dict:
    """Post the final review to GitHub."""
    if state.get("human_action") == "reject":
        logger.info("Review rejected by human — not posting to GitHub")
        return {}

    success = await post_pr_comment(
        state["repo"],
        state["pr_number"],
        state["final_report"],
    )

    if success:
        logger.info("Review posted to GitHub PR #%s", state["pr_number"])
    else:
        logger.error("Failed to post review to GitHub PR #%s", state["pr_number"])

    return {}


def should_post(state: PRReviewState) -> str:
    """Router — only post if human approved or edited."""
    action = state.get("human_action", "pending")
    if action in ("approve", "edit"):
        return "post"
    return "end"


def build_graph() -> StateGraph:
    graph = StateGraph(PRReviewState)

    graph.add_node("fetch", fetch_node)
    graph.add_node("review", review_node)
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("hitl", hitl_node)
    graph.add_node("post", post_node)

    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "review")
    graph.add_edge("review", "aggregate")
    graph.add_edge("aggregate", "hitl")
    graph.add_conditional_edges(
        "hitl",
        should_post,
        {"post": "post", "end": END},
    )
    graph.add_edge("post", END)

    return graph.compile()
