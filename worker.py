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
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            repo = body["repo"]
            pr_number = body["pr_number"]
            logger.info("Processing PR review: %s#%s", repo, pr_number)

            graph = build_graph()
            result = await graph.ainvoke({
                "repo": repo,
                "pr_number": pr_number,
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

            if result.get("error"):
                logger.error("Graph error: %s", result["error"])
                return

            review_id = result.get("review_id", "")
            if review_id:
                app_port = os.getenv("APP_PORT", "8000")
                logger.info(
                    "Review ready for human approval:\n"
                    "  View:    GET  http://localhost:%s/review/%s\n"
                    "  Approve: POST http://localhost:%s/review/%s/approve\n"
                    "  Edit:    POST http://localhost:%s/review/%s/edit\n"
                    "  Reject:  POST http://localhost:%s/review/%s/reject",
                    app_port, review_id,
                    app_port, review_id,
                    app_port, review_id,
                    app_port, review_id,
                )

        except Exception:
            logger.exception("Failed to process message")


async def main() -> None:
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    logger.info("Worker starting...")

    connection = await aio_pika.connect_robust(rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        logger.info("Listening on queue: %s", QUEUE_NAME)
        await queue.consume(process_message)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
