import logging
import os
from typing import Optional
from telegram import Bot, Update
from telegram.ext import Application
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    BasePersistence,
    DictPersistence,
    PersistenceInput,
)

from gptcli.telegram.listeners import TelegramChatListener
from gptcli.assistant import AssistantGlobalArgs, init_assistant

from gptcli.session import (
    ChatSession,
)


def init_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assistant = init_assistant(AssistantGlobalArgs(assistant_name="general"), {})
    session = ChatSession(assistant, TelegramChatListener(update.message))
    if "messages" in context.user_data:
        session.messages = context.user_data["messages"]
    return session


async def process_input(
    context: ContextTypes.DEFAULT_TYPE, session: ChatSession, text: str, overrides: dict
):
    await session.process_input(text, overrides)
    context.user_data["messages"] = session.messages


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! How can I help you today?",
    )


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logging.info(f"update: {update}")
    session = init_session(update, context)
    overrides = context.user_data.get("overrides", {})
    logging.info(f"overrides: {overrides}")
    session.listener = TelegramChatListener(update.message)
    await process_input(context, session, text, overrides)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = init_session(update, context)
    await process_input(context, session, "clear", {})


async def rerun_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = init_session(update, context)
    await process_input(context, session, "rerun", {})


async def set_override(
    parameter_name: str, update: Update, context: ContextTypes.DEFAULT_TYPE
):
    overrides = context.user_data.get("overrides", {})
    overrides[parameter_name] = context.args[0]
    context.user_data["overrides"] = overrides
    await update.message.reply_text(
        f"Set {parameter_name} to {context.args[0]}. Current overrides: {overrides}"
    )


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_override("model", update, context)


async def temperature_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await set_override("temperature", update, context)


async def top_p_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_override("top_p", update, context)


async def params_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    overrides = context.user_data.get("overrides", {})
    await update.message.reply_text(f"Current params: {overrides}")


async def post_init(app: Application):
    await app.bot.set_my_commands(
        [
            ("start", "Start the conversation"),
            ("clear", "Clear the conversation"),
            ("rerun", "Rerun the conversation"),
            ("model", "Set the model"),
            ("temp", "Set the temperature"),
            ("top_p", "Set the top_p"),
            ("params", "Show the current parameters"),
        ]
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logging.error(msg="Exception while handling an update:", exc_info=context.error)


def init_application(persistence: Optional[BasePersistence] = None) -> Application:
    bot = Bot(token=os.environ["TELEGRAM_API_TOKEN"])
    application_builder = ApplicationBuilder()
    application_builder.bot(bot).post_init(post_init)

    if persistence:
        application_builder.persistence(persistence)

    application = application_builder.build()

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message)
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("rerun", rerun_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("temperature", temperature_command))
    application.add_handler(CommandHandler("top_p", top_p_command))
    application.add_handler(CommandHandler("params", params_command))

    application.add_error_handler(error_handler)
    return application


def main():
    application = init_application(
        persistence=DictPersistence(
            store_data=PersistenceInput(
                bot_data=False, chat_data=False, user_data=True, callback_data=False
            )
        )
    )
    application.run_polling()


if __name__ == "__main__":
    main()
