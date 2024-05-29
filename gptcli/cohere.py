import os
import cohere
from typing import Iterator, List

from gptcli.completion import (
    CompletionEvent,
    CompletionProvider,
    Message,
    CompletionError,
    BadRequestError,
    MessageDeltaEvent,
    Pricing,
    UsageEvent,
)

api_key = os.environ.get("COHERE_API_KEY")

ROLE_MAP = {
    "system": "SYSTEM",
    "user": "USER",
    "assistant": "CHATBOT",
}


def map_message(message: Message) -> cohere.Message:
    if message["role"] == "system":
        return cohere.Message_System(message=message["content"])
    elif message["role"] == "user":
        return cohere.Message_User(message=message["content"])
    elif message["role"] == "assistant":
        return cohere.Message_Chatbot(message=message["content"])
    else:
        raise ValueError(f"Unknown message role: {message['role']}")


class CohereCompletionProvider(CompletionProvider):
    def __init__(self):
        self.client = cohere.Client(api_key=api_key)

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["p"] = args["top_p"]

        model = args["model"]

        if messages[0]["role"] == "system":
            kwargs["preamble"] = messages[0]["content"]
            messages = messages[1:]

        message = messages[-1]
        assert message["role"] == "user", "Last message must be user message"

        chat_history = [map_message(m) for m in messages[:-1]]

        try:
            if stream:
                response_iter = self.client.chat_stream(
                    chat_history=chat_history,
                    message=message["content"],
                    model=model,
                    **kwargs,
                )

                for response in response_iter:
                    if response.event_type == "text-generation":
                        yield MessageDeltaEvent(response.text)

                    if (
                        response.event_type == "stream-end"
                        and response.response.meta
                        and response.response.meta.tokens
                        and (pricing := COHERE_PRICING.get(args["model"]))
                    ):
                        input_tokens = int(
                            response.response.meta.tokens.input_tokens or 0
                        )
                        output_tokens = int(
                            response.response.meta.tokens.output_tokens or 0
                        )
                        total_tokens = input_tokens + output_tokens

                        yield UsageEvent.with_pricing(
                            prompt_tokens=input_tokens,
                            completion_tokens=output_tokens,
                            total_tokens=total_tokens,
                            pricing=pricing,
                        )

            else:
                response = self.client.chat(
                    chat_history=chat_history,
                    message=message["content"],
                    model=model,
                    **kwargs,
                )
                yield MessageDeltaEvent(response.text)

                if (
                    response.meta
                    and response.meta.tokens
                    and (pricing := COHERE_PRICING.get(args["model"]))
                ):
                    input_tokens = int(response.meta.tokens.input_tokens or 0)
                    output_tokens = int(response.meta.tokens.output_tokens or 0)
                    total_tokens = input_tokens + output_tokens

                    yield UsageEvent.with_pricing(
                        prompt_tokens=input_tokens,
                        completion_tokens=output_tokens,
                        total_tokens=total_tokens,
                        pricing=pricing,
                    )

        except cohere.BadRequestError as e:
            raise BadRequestError(e.body) from e
        except (
            cohere.TooManyRequestsError,
            cohere.InternalServerError,
            cohere.core.api_error.ApiError,  # type: ignore
        ) as e:
            raise CompletionError(e.body) from e


COHERE_PRICING: dict[str, Pricing] = {
    "command-r": {
        "prompt": 0.5 / 1_000_000,
        "response": 1.5 / 1_000_000,
    },
    "command-r-plus": {
        "prompt": 3.0 / 1_000_000,
        "response": 15.0 / 1_000_000,
    },
}
