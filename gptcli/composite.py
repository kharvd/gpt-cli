from gptcli.completion import Message, ModelOverrides
from gptcli.session import ChatListener, ResponseStreamer


from typing import List, Optional


class CompositeResponseStreamer(ResponseStreamer):
    def __init__(self, streamers: List[ResponseStreamer]):
        self.streamers = streamers

    def __enter__(self):
        for streamer in self.streamers:
            streamer.__enter__()
        return self

    def on_message_delta(self, message_delta: Message):
        for streamer in self.streamers:
            streamer.on_message_delta(message_delta)

    def on_function_result(self, result: dict):
        for streamer in self.streamers:
            streamer.on_function_result(result)

    def __exit__(self, *args):
        for streamer in self.streamers:
            streamer.__exit__(*args)


class CompositeChatListener(ChatListener):
    def __init__(self, listeners: List[ChatListener]):
        self.listeners = listeners

    def on_chat_start(self):
        for listener in self.listeners:
            listener.on_chat_start()

    def on_chat_clear(self):
        for listener in self.listeners:
            listener.on_chat_clear()

    def on_chat_rerun(self, success: bool):
        for listener in self.listeners:
            listener.on_chat_rerun(success)

    def on_error(self, e: Exception):
        for listener in self.listeners:
            listener.on_error(e)

    def response_streamer(self) -> ResponseStreamer:
        return CompositeResponseStreamer(
            [listener.response_streamer() for listener in self.listeners]
        )

    def on_chat_message(self, message: Message):
        for listener in self.listeners:
            listener.on_chat_message(message)

    def on_chat_response(
        self, messages: List[Message], response: Message, overrides: ModelOverrides
    ):
        for listener in self.listeners:
            listener.on_chat_response(messages, response, overrides)

    def on_function_call(self, function_name: str, **kwargs) -> Optional[str]:
        for listener in self.listeners:
            result = listener.on_function_call(function_name, **kwargs)
            if result is not None:
                return result
