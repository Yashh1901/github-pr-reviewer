# agents/hitl.py
import json
import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis

from api.config import get_settings

logger = logging.getLogger(__name__)
HITL_TTL_SECONDS = 60 * 60 * 24


async def get_redis():
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def save_pending_review(state: dict) -> str:
    review_id = str(uuid.uuid4())
    key = f"hitl:pending:{review_id}"

    payload = {
        "review_id": review_id,
        "repo": state["repo"],
        "pr_number": state["pr_number"],
        "final_report": state["final_report"],
        "created_at": datetime.now(UTC).isoformat(),
        "status": "pending",
    }

    r = await get_redis()
    async with r:
        await r.set(key, json.dumps(payload), ex=HITL_TTL_SECONDS)  # ← fixed

    logger.info("Saved pending review %s for %s#%s", review_id, state["repo"], state["pr_number"])
    return review_id


async def get_pending_review(review_id: str) -> dict | None:
    key = f"hitl:pending:{review_id}"
    r = await get_redis()
    async with r:
        data = await r.get(key)
    return json.loads(data) if data else None


async def resolve_review(review_id: str, action: str, edited_report: str | None = None) -> dict | None:
    key = f"hitl:pending:{review_id}"
    r = await get_redis()
    async with r:
        data = await r.get(key)
        if not data:
            return None
        payload = json.loads(data)
        payload["status"] = action
        payload["resolved_at"] = datetime.now(UTC).isoformat()
        if edited_report:
            payload["final_report"] = edited_report
        await r.set(key, json.dumps(payload), ex=HITL_TTL_SECONDS)  # ← fixed
    return payload
