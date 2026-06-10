class SecurityAgent:
    """Scans PR diff for security vulnerabilities."""

    def __init__(self, llm):
        self.llm = llm

    async def review(self, diff: str) -> str:
        # TODO: implement full prompt + LLM call in Phase 4
        return "Security review placeholder"