# agents/code_reviewer.py
import logging

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.prompts import CODE_REVIEW_PROMPT

logger = logging.getLogger(__name__)


class CodeReviewerAgent:
    """Analyzes PR diff for bugs, logic errors, and style issues."""

    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    async def review(self, pr_data: dict) -> str:
        logger.info("Code reviewer analyzing PR: %s", pr_data.get("title"))

        prompt = CODE_REVIEW_PROMPT.format(
            title=pr_data["title"],
            author=pr_data["author"],
            base_branch=pr_data["base_branch"],
            diff=pr_data["diff"],
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception:
            logger.exception("Code reviewer LLM call failed")
            return "## Code Review\n\nCode review unavailable — LLM error."
