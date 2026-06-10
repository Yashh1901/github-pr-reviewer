# worker.py
import asyncio
import json
import logging
import os

import aio_pika
from dotenv import load_dotenv

from agents.supervisor import build_graph

load_dotenv()



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

QUEUE_NAME = "pr_review"


async def process_message(message: aio_pika.IncomingMessage) -> None:
    """Process a single PR review job from the queue."""
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            repo = body["repo"]
            pr_number = body["pr_number"]
            logger.info("Processing PR review job: %s#%s", repo, pr_number)

            graph = build_graph()

            initial_state = {
                "repo": repo,
                "pr_number": pr_number,
                "pr_data": {},
                "code_review": "",
                "security_review": "",
                "test_review": "",
                "final_report": "",
                "human_approved": False,
                "error": "",
            }

            result = await graph.ainvoke(initial_state)

            if result.get("error"):
                logger.error("Graph failed for %s#%s: %s", repo, pr_number, result["error"])
                return

            logger.info(
                "Review complete for %s#%s — report length: %d chars",
                repo, pr_number, len(result["final_report"])
            )
            logger.info("Final report preview:\n%s", result["final_report"][:500])

        except Exception:
            logger.exception("Failed to process message")


async def main() -> None:
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    logger.info("Worker starting — connecting to RabbitMQ...")

    connection = await aio_pika.connect_robust(rabbitmq_url)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        logger.info("Worker ready — listening on queue: %s", QUEUE_NAME)

        await queue.consume(process_message)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
