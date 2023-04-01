import logging
import os
from telegram import Bot, Update
from telegram.ext import Application
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

from gptcli.telegram.listeners import TelegramChatListener
from gptcli.assistant import AssistantGlobalArgs, init_assistant

from gptcli.session import (
    ChatSession,
)
from gptcli.term_utils import COMMAND_CLEAR

TOKEN = os.environ["TELEGRAM_TOKEN"]

CHAT = range(1)


def init_session(update: Update):
    assistant = init_assistant(AssistantGlobalArgs(assistant_name="general"), {})
    return ChatSession(assistant, TelegramChatListener(update.message))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["session"] = init_session(update)
    await update.message.reply_text(
        "Hi! How can I help you today?",
    )

    return CHAT


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    logging.info(f"update: {update}")
    if "session" not in context.user_data:
        context.user_data["session"] = init_session(update)

    session = context.user_data["session"]

    overrides = context.user_data.get("overrides", {})

    logging.info(f"overrides: {overrides}")

    session.listener = TelegramChatListener(update.message)
    await session.process_input(text, overrides)
    return CHAT


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = context.user_data["session"]
    await session.process_input("clear", {})
    return CHAT


async def rerun_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = context.user_data["session"]
    await session.process_input("rerun", {})
    return CHAT


async def set_override(
    parameter_name: str, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    overrides = context.user_data.get("overrides", {})
    overrides[parameter_name] = context.args[0]
    context.user_data["overrides"] = overrides
    await update.message.reply_text(
        f"Set {parameter_name} to {context.args[0]}. Current overrides: {overrides}"
    )
    return CHAT


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await set_override("model", update, context)


async def temperature_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await set_override("temperature", update, context)


async def top_p_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await set_override("top_p", update, context)


async def params_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    overrides = context.user_data.get("overrides", {})
    await update.message.reply_text(f"Current params: {overrides}")
    return CHAT


async def post_init(app: Application):
    await app.bot.set_my_commands(
        [
            ("start", "Start the conversation"),
            ("clear", "Clear the conversation"),
            ("rerun", "Rerun the conversation"),
            ("model", "Set the model"),
            ("temperature", "Set the temperature"),
            ("top_p", "Set the top_p"),
            ("params", "Show the current parameters"),
        ]
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logging.error(msg="Exception while handling an update:", exc_info=context.error)


def main():
    logging.basicConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = Bot(token=TOKEN)
    application = ApplicationBuilder().bot(bot).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message),
        ],
        states={
            CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message),
            ],
        },
        fallbacks=[
            CommandHandler("clear", clear_command),
            CommandHandler("rerun", rerun_command),
            CommandHandler("model", model_command),
            CommandHandler("temperature", temperature_command),
            CommandHandler("top_p", top_p_command),
            CommandHandler("params", params_command),
        ],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
