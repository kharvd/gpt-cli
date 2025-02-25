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
    ThinkingDeltaEvent,
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
        # Default max tokens and max allowed by Claude API
        DEFAULT_MAX_TOKENS = 4096
        CLAUDE_MAX_TOKENS_LIMIT = 64000

        # Set initial max_tokens value
        max_tokens = DEFAULT_MAX_TOKENS

        # If thinking mode is enabled, adjust max_tokens accordingly
        if "thinking_budget" in args and "claude-3-7" in args["model"]:
            thinking_budget = args["thinking_budget"]
            # Max tokens must be greater than thinking budget
            # Calculate required max_tokens, but don't exceed the API limit
            response_tokens = min(
                DEFAULT_MAX_TOKENS, CLAUDE_MAX_TOKENS_LIMIT - thinking_budget
            )
            max_tokens = min(thinking_budget + response_tokens, CLAUDE_MAX_TOKENS_LIMIT)

        kwargs = {
            "stop_sequences": [anthropic.HUMAN_PROMPT],
            "max_tokens": max_tokens,
            "model": args["model"],
        }

        # Check if thinking mode is enabled
        thinking_enabled = "thinking_budget" in args and "claude-3-7" in args["model"]

        # Handle temperature and top_p
        if thinking_enabled:
            # When thinking is enabled, temperature must be set to 1.0 and top_p must be unset
            kwargs["temperature"] = 1.0
            # Do not set top_p in this case
        else:
            # Normal mode - apply user settings
            if "temperature" in args:
                kwargs["temperature"] = args["temperature"]
            if "top_p" in args:
                kwargs["top_p"] = args["top_p"]

        # Handle thinking mode
        if thinking_enabled:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": args["thinking_budget"],
            }

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
                            if event.delta.type == "thinking_delta":
                                yield ThinkingDeltaEvent(event.delta.thinking)
                            elif event.delta.type == "text_delta":
                                yield MessageDeltaEvent(event.delta.text)
                            # Skip other delta types
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
                yield MessageDeltaEvent(
                    "".join(
                        c.text if c.type == "text" else "" for c in response.content
                    )
                )
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

CLAUDE_3_7_SONNET_PRICING: Pricing = {
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
        elif "3-7-sonnet" in model:
            pricing = CLAUDE_3_7_SONNET_PRICING
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
