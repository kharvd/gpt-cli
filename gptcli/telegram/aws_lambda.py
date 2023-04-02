import json
import logging
import asyncio
from telegram import Update
from telegram.ext import BasePersistence, PersistenceInput
import boto3

from gptcli.telegram.bot import init_application

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DynamoDBPersistence(BasePersistence):
    def __init__(self):
        super().__init__(
            PersistenceInput(
                bot_data=False, chat_data=False, user_data=True, callback_data=False
            )
        )
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table("gptcli")

    async def get_user_data(self):
        return {}

    async def get_chat_data(self):
        pass

    async def get_bot_data(self):
        pass

    async def get_callback_data(self):
        pass

    async def get_conversations(self, name: str):
        pass

    async def update_conversation(self, name, key, new_state) -> None:
        pass

    async def update_user_data(self, user_id: int, data) -> None:
        self.table.put_item(
            Item={
                "id": user_id,
                "user_data": data,
            }
        )

    async def update_chat_data(self, chat_id: int, data) -> None:
        pass

    async def update_bot_data(self, data) -> None:
        pass

    async def update_callback_data(self, data) -> None:
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def drop_user_data(self, user_id: int) -> None:
        self.table.delete_item(Key={"id": user_id})

    async def refresh_user_data(self, user_id: int, user_data) -> None:
        response = self.table.get_item(Key={"id": str(user_id)})
        data = response.get("Item", {}).get("user_data", {})
        for key, value in data.items():
            user_data[key] = value

    async def refresh_chat_data(self, chat_id: int, chat_data) -> None:
        pass

    async def refresh_bot_data(self, bot_data) -> None:
        pass

    async def flush(self) -> None:
        pass


async def handler(event, context):
    logger.info(f"event: {event}")
    logger.info(f"context: {context}")

    application = init_application(DynamoDBPersistence())
    await application.initialize()

    update = Update.de_json(json.loads(event["body"]), application.bot)
    await application.process_update(update)
    await application.shutdown()

    return {"statusCode": 200}


def lambda_handler(event, context):
    asyncio.run(handler(event, context))
    return {"statusCode": 200}
