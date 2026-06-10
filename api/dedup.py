# api/dedup.py
import logging

import redis.asyncio as aioredis

from api.config import get_settings

logger = logging.getLogger(__name__)

DEDUP_TTL_SECONDS = 300  # 5 minutes


async def get_redis():
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def is_duplicate(repo: str, pr_number: int, sha: str) -> bool:
    """Returns True if this exact PR+sha was already queued recently."""
    key = f"pr_review:{repo}:{pr_number}:{sha}"
    try:
        r = await get_redis()
        async with r:
            already_seen = await r.get(key)
            if already_seen:
                logger.info("Duplicate PR event skipped: %s", key)
                return True
            await r.setex(key, DEDUP_TTL_SECONDS, "1")
            return False
    except Exception:
        logger.exception("Redis error during dedup check — allowing through")
        return False  # fail open: if Redis is down, don't block events