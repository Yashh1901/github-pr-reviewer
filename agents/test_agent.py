# agents/test_agent.py
import logging

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.prompts import TEST_REVIEW_PROMPT

logger = logging.getLogger(__name__)


class TestAgent:
    """Checks test coverage and suggests missing test cases."""

    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    async def review(self, pr_data: dict) -> str:
        logger.info("Test agent analyzing PR: %s", pr_data.get("title"))

        prompt = TEST_REVIEW_PROMPT.format(
            title=pr_data["title"],
            author=pr_data["author"],
            diff=pr_data["diff"],
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception:
            logger.exception("Test agent LLM call failed")
            return "## Test Coverage Review\n\nTest review unavailable — LLM error."
