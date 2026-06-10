class CodeReviewerAgent:
    """Analyzes PR diff for bugs, logic errors, style issues."""

    def __init__(self, llm):
        self.llm = llm

    async def review(self, diff: str) -> str:
        # TODO: implement full prompt + LLM call in Phase 4
        return "Code review placeholder"