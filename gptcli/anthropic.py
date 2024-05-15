import os
from typing import Iterator, List, Optional
import anthropic

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

api_key = os.environ.get("ANTHROPIC_API_KEY")


def get_client():
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    return anthropic.Anthropic(api_key=api_key)


class AnthropicCompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        kwargs = {
            "stop_sequences": [anthropic.HUMAN_PROMPT],
            "max_tokens": 4096,
            "model": args["model"],
        }

        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        if len(messages) > 0 and messages[0]["role"] == "system":
            kwargs["system"] = messages[0]["content"]
            messages = messages[1:]

        kwargs["messages"] = messages

        client = get_client()
        input_tokens = None
        try:
            if stream:
                with client.messages.stream(**kwargs) as completion:
                    for event in completion:
                        if event.type == "content_block_delta":
                            yield MessageDeltaEvent(event.delta.text)
                        if event.type == "message_start":
                            input_tokens = event.message.usage.input_tokens
                        if (
                            event.type == "message_delta"
                            and (pricing := claude_pricing(args["model"]))
                            and input_tokens
                        ):
                            yield UsageEvent.with_pricing(
                                prompt_tokens=input_tokens,
                                completion_tokens=event.usage.output_tokens,
                                total_tokens=input_tokens + event.usage.output_tokens,
                                pricing=pricing,
                            )

            else:
                response = client.messages.create(**kwargs, stream=False)
                yield MessageDeltaEvent("".join(c.text for c in response.content))
                if pricing := claude_pricing(args["model"]):
                    yield UsageEvent.with_pricing(
                        prompt_tokens=response.usage.input_tokens,
                        completion_tokens=response.usage.output_tokens,
                        total_tokens=response.usage.input_tokens
                        + response.usage.output_tokens,
                        pricing=pricing,
                    )
        except anthropic.BadRequestError as e:
            raise BadRequestError(e.message) from e
        except anthropic.APIError as e:
            raise CompletionError(e.message) from e


CLAUDE_PRICE_PER_TOKEN: Pricing = {
    "prompt": 11.02 / 1_000_000,
    "response": 32.68 / 1_000_000,
}

CLAUDE_INSTANT_PRICE_PER_TOKEN: Pricing = {
    "prompt": 1.63 / 1_000_000,
    "response": 5.51 / 1_000_000,
}

CLAUDE_3_OPUS_PRICING: Pricing = {
    "prompt": 15.0 / 1_000_000,
    "response": 75.0 / 1_000_000,
}

CLAUDE_3_SONNET_PRICING: Pricing = {
    "prompt": 3.0 / 1_000_000,
    "response": 15.0 / 1_000_000,
}

CLAUDE_3_HAIKU_PRICING: Pricing = {
    "prompt": 0.25 / 1_000_000,
    "response": 1.25 / 1_000_000,
}


def claude_pricing(model: str) -> Optional[Pricing]:
    if "instant" in model:
        pricing = CLAUDE_INSTANT_PRICE_PER_TOKEN
    elif "claude-3" in model:
        if "opus" in model:
            pricing = CLAUDE_3_OPUS_PRICING
        elif "sonnet" in model:
            pricing = CLAUDE_3_SONNET_PRICING
        elif "haiku" in model:
            pricing = CLAUDE_3_HAIKU_PRICING
        else:
            return None
    elif "claude-2" in model:
        pricing = CLAUDE_PRICE_PER_TOKEN
    else:
        return None
    return pricing
