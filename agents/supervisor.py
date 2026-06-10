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
    error: str


def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
    )


async def fetch_node(state: PRReviewState) -> dict:
    """Node 1 — fetch PR data from GitHub."""
    logger.info("Fetching PR data: %s#%s", state["repo"], state["pr_number"])
    try:
        pr_data = fetch_pr_data(state["repo"], state["pr_number"])
        return {"pr_data": pr_data}
    except Exception as e:
        logger.exception("Failed to fetch PR data")
        return {"error": str(e), "pr_data": {}}


async def review_node(state: PRReviewState) -> dict:
    """Node 2 — run all 3 specialist agents IN PARALLEL."""
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
    """Node 3 — merge all 3 reviews into one final report."""

    # If fetch failed, skip LLM aggregation entirely
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

    return {
        "final_report": final_report,
        "human_approved": False,
    }

# async def aggregate_node(state: PRReviewState) -> dict:
#     """Node 3 — merge all 3 reviews into one final report."""
#     logger.info("Aggregating reviews for PR #%s", state["pr_number"])

#     llm = get_llm()
#     prompt = AGGREGATOR_PROMPT.format(
#         code_review=state["code_review"],
#         security_review=state["security_review"],
#         test_review=state["test_review"],
#     )

#     try:
#         response = await llm.ainvoke([HumanMessage(content=prompt)])
#         final_report = response.content
#     except Exception:
#         logger.exception("Aggregator LLM call failed")
#         final_report = "\n\n".join([
#             state["code_review"],
#             state["security_review"],
#             state["test_review"],
#         ])

#     return {
#         "final_report": final_report,
#         "human_approved": False,
#     }


def build_graph() -> StateGraph:
    """Build and compile the LangGraph multi-agent pipeline."""
    graph = StateGraph(PRReviewState)

    graph.add_node("fetch", fetch_node)
    graph.add_node("review", review_node)
    graph.add_node("aggregate", aggregate_node)

    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "review")
    graph.add_edge("review", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()
