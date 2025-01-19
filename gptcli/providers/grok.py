import os
import openai
from openai import OpenAI

from typing import Iterator, List, Optional, cast
from openai.types.chat import ChatCompletionMessageParam
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


class GrokCompletionProvider(CompletionProvider):
    def __init__(self):
        self.api_key = os.environ.get("XAI_API_KEY") or openai.api_key
        if not self.api_key:
            raise ValueError("XAI_API_KEY environment variable not set and openai.api_key not set")
        self.base_url = "https://api.x.ai/v1"

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        # Save old openai values
        old_api_key = openai.api_key
        old_base_url = openai.base_url
        # Set openai api_key and base_url temporarily
        openai.api_key = self.api_key
        openai.base_url = self.base_url

        try:
            kwargs = {}
            if "temperature" in args:
                kwargs["temperature"] = args["temperature"]
            if "top_p" in args:
                kwargs["top_p"] = args["top_p"]

            model = args["model"]

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            if stream:
                response_iter = client.chat.completions.create(
                    messages=cast(List[ChatCompletionMessageParam], messages),
                    stream=True,
                    model=model,
                    stream_options={"include_usage": True},
                    **kwargs,
                )

                for response in response_iter:
                    if (
                        len(response.choices) > 0
                        and response.choices[0].finish_reason is None
                        and response.choices[0].delta.content
                    ):
                        yield MessageDeltaEvent(response.choices[0].delta.content)

                    if response.usage and (pricing := grok_pricing(args["model"])):
                        yield UsageEvent.with_pricing(
                            prompt_tokens=response.usage.prompt_tokens,
                            completion_tokens=response.usage.completion_tokens,
                            total_tokens=response.usage.total_tokens,
                            pricing=pricing,
                        )
            else:
                response = client.chat.completions.create(
                    messages=messages,
                    model=model,
                    stream=False,
                    **kwargs,
                )
                next_choice = response.choices[0]
                if next_choice.message.content:
                    yield MessageDeltaEvent(next_choice.message.content)
                if response.usage and (pricing := grok_pricing(args["model"])):
                    yield UsageEvent.with_pricing(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        pricing=pricing,
                    )

        except openai.error.InvalidRequestError as e:
            raise BadRequestError(str(e)) from e
        except openai.error.OpenAIError as e:
            raise CompletionError(str(e)) from e
        finally:
            # Restore old openai values
            openai.api_key = old_api_key
            openai.base_url = old_base_url


def grok_pricing(model: str) -> Optional[Pricing]:
    if model.startswith("grok-beta"):
        return {
            "prompt": 5.00 / 1_000_000,
            "response": 15.00 / 1_000_000,
        }
