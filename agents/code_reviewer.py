# agents/code_reviewer.py


class CodeReviewerAgent:
    """Analyzes PR diff for bugs, logic errors, style issues."""

    def __init__(self, llm):
        self.llm = llm

    async def review(self, diff: str) -> str:
        # TODO: implement in Phase 4
        return "Code review placeholder"
