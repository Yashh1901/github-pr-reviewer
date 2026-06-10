# api/queue.py
import json
import logging
from datetime import UTC, datetime

import aio_pika

from api.config import get_settings

logger = logging.getLogger(__name__)

QUEUE_NAME = "pr_review"


async def get_connection():
    settings = get_settings()
    return await aio_pika.connect_robust(settings.rabbitmq_url)


async def publish_pr_review_job(
    repo: str,
    pr_number: int,
    action: str,
    sha: str,
) -> bool:
    """Publish a PR review job to RabbitMQ. Returns True if published."""
    try:
        connection = await get_connection()
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(
                QUEUE_NAME,
                durable=True,
            )

            message_body = {
                "repo": repo,
                "pr_number": pr_number,
                "action": action,
                "sha": sha,
                "queued_at": datetime.now(UTC).isoformat(),
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message_body).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=queue.name,
            )

            logger.info(
                "Published PR review job: %s#%s (%s)",
                repo, pr_number, action
            )
            return True

    except Exception:
        logger.exception("Failed to publish PR review job to RabbitMQ")
        return False
