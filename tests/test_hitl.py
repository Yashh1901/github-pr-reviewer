# tests/test_hitl.py
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_approve_posts_comment():
    mock_review = {
        "review_id": "abc-123",
        "repo": "user/repo",
        "pr_number": 42,
        "final_report": "## Review\nLooks good!",
        "status": "approve",
    }

    with (
        patch("api.review.get_pending_review", new_callable=AsyncMock, return_value=mock_review),
        patch("api.review.resolve_review", new_callable=AsyncMock, return_value=mock_review),
        patch("api.review.post_pr_comment", new_callable=AsyncMock, return_value=True),
    ):
        from httpx import ASGITransport, AsyncClient

        from api.webhook import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/review/abc-123/approve")

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["posted"] is True


@pytest.mark.asyncio
async def test_reject_does_not_post():
    mock_review = {
        "review_id": "abc-123",
        "repo": "user/repo",
        "pr_number": 42,
        "final_report": "## Review",
        "status": "reject",
    }

    with (
        patch("api.review.get_pending_review", new_callable=AsyncMock, return_value=mock_review),
        patch("api.review.resolve_review", new_callable=AsyncMock, return_value=mock_review),
        patch("api.review.post_pr_comment", new_callable=AsyncMock) as mock_post,
    ):
        from httpx import ASGITransport, AsyncClient

        from api.webhook import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/review/abc-123/reject")

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["posted"] is False
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_get_review_not_found():
    with patch("api.review.get_pending_review", new_callable=AsyncMock, return_value=None):
        from httpx import ASGITransport, AsyncClient

        from api.webhook import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/review/nonexistent-id")

    assert resp.status_code == 404
