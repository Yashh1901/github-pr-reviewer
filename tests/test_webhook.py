import hashlib
import hmac

import pytest
from httpx import ASGITransport, AsyncClient

from api.webhook import app

SECRET = "test_secret"

def make_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_webhook_invalid_signature():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/webhook",
            json={"action": "opened"},
            headers={"X-Hub-Signature-256": "sha256=invalid"}
        )
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_webhook_pr_opened(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    body = b'{"action":"opened","pull_request":{"number":42},"repository":{"full_name":"user/repo"}}'
    sig = make_signature(body, SECRET)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            }
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
