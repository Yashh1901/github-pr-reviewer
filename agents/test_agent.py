# agents/test_agent.py


class TestAgent:
    """Checks test coverage and suggests missing tests."""

    def __init__(self, llm):
        self.llm = llm

    async def review(self, diff: str) -> str:
        # TODO: implement in Phase 4
        return "Test review placeholder"
