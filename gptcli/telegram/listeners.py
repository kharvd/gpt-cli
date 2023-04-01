import logging
from openai import InvalidRequestError, OpenAIError
from gptcli.session import ChatListener, InvalidArgumentError, ResponseStreamer
from telegram import Message as TelegramMessage


class TelegramResponseStreamer(ResponseStreamer):
    def __init__(self, user_telegram_message: TelegramMessage):
        self.user_telegram_message = user_telegram_message
        self.telegram_message = None
        self.message_buffer = ""
        self.message_text = ""

    async def __aenter__(self):
        self.telegram_message = await self.user_telegram_message.reply_text("...")
        return self

    async def _maybe_edit(self) -> None:
        prev_message = self.message_text.strip()

        self.message_text += self.message_buffer
        self.message_buffer = ""

        stripped_message = self.message_text.strip()

        if stripped_message != "" and stripped_message != prev_message:
            await self.telegram_message.edit_text(stripped_message)

    async def on_next_token(self, token: str):
        self.message_buffer += token

        if len(self.message_buffer) < 10 and token != "":
            return

        await self._maybe_edit()

    async def __aexit__(self, *args):
        await self._maybe_edit()


class TelegramChatListener(ChatListener):
    def __init__(self, user_telegram_message: TelegramMessage):
        self.user_telegram_message = user_telegram_message

    async def _send_message(self, text: str):
        await self.user_telegram_message.reply_text(text)

    async def on_chat_clear(self):
        await self._send_message("Cleared the conversation.")

    async def on_chat_rerun(self, success: bool):
        if success:
            await self._send_message("Re-running the last message.")
        else:
            await self._send_message("Nothing to re-run.")

    async def on_error(self, e: Exception):
        if isinstance(e, InvalidRequestError):
            await self._send_message(
                f"Request Error. The last prompt was not saved: {type(e)}: {e}"
            )
        elif isinstance(e, OpenAIError):
            await self._send_message(f"API Error: {type(e)}: {e}")
        elif isinstance(e, InvalidArgumentError):
            await self._send_message(e.message)
        else:
            await self._send_message(f"Error: {type(e)}: {e}")

    def response_streamer(self) -> ResponseStreamer:
        return TelegramResponseStreamer(self.user_telegram_message)
