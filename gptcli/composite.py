import asyncio
from gptcli.assistant import Message
from gptcli.session import ChatListener, ResponseStreamer


from typing import List


class CompositeResponseStreamer(ResponseStreamer):
    def __init__(self, streamers: List[ResponseStreamer]):
        self.streamers = streamers

    async def __aenter__(self):
        await asyncio.gather(*[streamer.__aenter__() for streamer in self.streamers])
        return self

    async def on_next_token(self, token: str):
        await asyncio.gather(
            *[streamer.on_next_token(token) for streamer in self.streamers]
        )

    async def __aexit__(self, *args):
        await asyncio.gather(
            *[streamer.__aexit__(*args) for streamer in self.streamers]
        )


class CompositeChatListener(ChatListener):
    def __init__(self, listeners: List[ChatListener]):
        self.listeners = listeners

    async def on_chat_start(self):
        await asyncio.gather(*[listener.on_chat_start() for listener in self.listeners])

    async def on_chat_clear(self):
        await asyncio.gather(*[listener.on_chat_clear() for listener in self.listeners])

    async def on_chat_rerun(self, success: bool):
        await asyncio.gather(
            *[listener.on_chat_rerun(success) for listener in self.listeners]
        )

    async def on_error(self, e: Exception):
        await asyncio.gather(*[listener.on_error(e) for listener in self.listeners])

    def response_streamer(self) -> ResponseStreamer:
        return CompositeResponseStreamer(
            [listener.response_streamer() for listener in self.listeners]
        )

    async def on_chat_message(self, message: Message):
        await asyncio.gather(
            *[listener.on_chat_message(message) for listener in self.listeners]
        )
