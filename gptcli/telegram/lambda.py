import json
import logging
import asyncio
from telegram import Update

from gptcli.telegram.bot import init_application

logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def handler(event, context):
    logger.info(f"event: {event}")
    logger.info(f"context: {context}")

    application = init_application()
    await application.initialize()

    update = Update.de_json(json.loads(event["body"]), application.bot)
    await application.process_update(update)

    return {"statusCode": 200}


def lambda_handler(event, context):
    asyncio.run(handler(event, context))
    return {"statusCode": 200}
