# tests/test_agents.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_graph_builds():
    from agents.supervisor import build_graph
    graph = build_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_full_graph_flow():
    """Test the full graph with mocked LLM, GitHub API, and Redis."""
    from agents.supervisor import build_graph

    mock_pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "author": "testuser",
        "base_branch": "main",
        "head_branch": "feature",
        "files_changed": 2,
        "additions": 10,
        "deletions": 5,
        "files": [],
        "diff": "diff --git a/test.py\n+def hello(): pass",
    }

    mock_response = MagicMock()
    mock_response.content = "## Review\nLooks good!"

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_redis.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("agents.supervisor.fetch_pr_data", return_value=mock_pr_data),
        patch("agents.supervisor.get_llm") as mock_llm_factory,
        patch("agents.hitl.get_redis", return_value=mock_redis),
    ):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        graph = build_graph()
        result = await graph.ainvoke({
            "repo": "user/repo",
            "pr_number": 1,
            "pr_data": {},
            "code_review": "",
            "security_review": "",
            "test_review": "",
            "final_report": "",
            "human_approved": False,
            "human_action": "pending",
            "review_id": "",
            "error": "",
        })

    assert result["pr_data"] == mock_pr_data
    assert result["code_review"] != ""
    assert result["security_review"] != ""
    assert result["test_review"] != ""
    assert result["final_report"] != ""
    assert result["human_approved"] is False


@pytest.mark.asyncio
async def test_graph_handles_fetch_error():
    """Graph should degrade gracefully when GitHub API fails."""
    from agents.supervisor import build_graph

    with patch(
        "agents.supervisor.fetch_pr_data",
        side_effect=Exception("GitHub API down"),
    ):
        graph = build_graph()
        result = await graph.ainvoke({
            "repo": "user/repo",
            "pr_number": 99,
            "pr_data": {},
            "code_review": "",
            "security_review": "",
            "test_review": "",
            "final_report": "",
            "human_approved": False,
            "human_action": "pending",
            "review_id": "",
            "error": "",
        })

    assert result["error"] != ""
    assert "Skipped" in result["code_review"]
    assert "could not be completed" in result["final_report"]
