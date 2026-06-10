from fastapi import FastAPI, Request, HTTPException, Header
import hashlib
import hmac
import os

app = FastAPI(title="GitHub PR Reviewer")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if not _verify_signature(body, secret, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "")

    if event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize"):
            # TODO: enqueue to RabbitMQ in Phase 2
            pr_number = payload["pull_request"]["number"]
            repo = payload["repository"]["full_name"]
            return {"status": "queued", "pr": pr_number, "repo": repo}

    return {"status": "ignored"}

def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)