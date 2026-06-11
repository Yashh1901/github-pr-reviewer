# api/webhook.py
import hashlib
import hmac
import logging

from fastapi import FastAPI, Header, HTTPException, Request

from api.dedup import is_duplicate
from api.queue import publish_pr_review_job
from api.review import router as review_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub PR Reviewer", version="0.2.0")
app.include_router(review_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
):
    body = await request.body()

    # Read fresh every request — not cached — so tests can patch via env
    import os
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if not _verify_signature(body, secret, x_hub_signature_256):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "")

    if event == "ping":
        return {"status": "pong", "message": "Webhook configured successfully!"}

    if event != "pull_request":
        return {"status": "ignored", "event": event}

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": action}

    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]
    pr_number = pr["number"]
    sha = pr["head"]["sha"]

    duplicate = await is_duplicate(repo, pr_number, sha)
    if duplicate:
        return {"status": "duplicate", "pr": pr_number, "repo": repo}

    published = await publish_pr_review_job(
        repo=repo,
        pr_number=pr_number,
        action=action,
        sha=sha,
    )

    if not published:
        raise HTTPException(status_code=503, detail="Failed to queue review job")

    return {"status": "queued", "repo": repo, "pr": pr_number, "sha": sha}


def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    if not signature or not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
