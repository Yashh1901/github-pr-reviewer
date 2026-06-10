# agents/security_agent.py
import logging

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.prompts import SECURITY_REVIEW_PROMPT

logger = logging.getLogger(__name__)


class SecurityAgent:
    """Scans PR diff for security vulnerabilities."""

    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    async def review(self, pr_data: dict) -> str:
        logger.info("Security agent analyzing PR: %s", pr_data.get("title"))

        prompt = SECURITY_REVIEW_PROMPT.format(
            title=pr_data["title"],
            author=pr_data["author"],
            diff=pr_data["diff"],
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content
        except Exception:
            logger.exception("Security agent LLM call failed")
            return "## Security Review\n\nSecurity review unavailable — LLM error."
