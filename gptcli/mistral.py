from typing import Iterator, List
import os
from gptcli.completion import CompletionProvider, Message
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

api_key = os.environ.get("MISTRAL_API_KEY")


class MistralCompletionProvider(CompletionProvider):
    def __init__(self):
        self.client = MistralClient(api_key=api_key)

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]
        
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in messages
        ]

        if stream:
            response_iter = self.client.chat_stream(
                model=args["model"],
                messages=messages,
                **kwargs,
            )

            for response in response_iter:
                next_choice = response.choices[0]
                if next_choice.finish_reason is None and next_choice.delta.content:
                    yield next_choice.delta.content
        else:
            response = self.client.chat(
                model=args["model"],
                messages=messages,
                **kwargs,
            )
            next_choice = response.choices[0]
            if next_choice.message.content:
                yield next_choice.message.content
