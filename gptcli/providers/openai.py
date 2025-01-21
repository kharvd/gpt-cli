import re
from typing import Iterator, List, Optional, cast
import openai
from openai import OpenAI
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


class OpenAICompletionProvider(CompletionProvider):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.client = OpenAI(
            api_key=api_key or openai.api_key, base_url=base_url or openai.base_url
        )

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        model = args["model"]
        if model.startswith("oai-compat:"):
            model = model[len("oai-compat:") :]

        if model.startswith("oai-azure:"):
            model = model[len("oai-azure:") :]

        try:
            if stream:
                response_iter = self.client.chat.completions.create(
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

                    if response.usage and (pricing := gpt_pricing(args["model"])):
                        yield UsageEvent.with_pricing(
                            prompt_tokens=response.usage.prompt_tokens,
                            completion_tokens=response.usage.completion_tokens,
                            total_tokens=response.usage.total_tokens,
                            pricing=pricing,
                        )
            else:
                response = self.client.chat.completions.create(
                    messages=cast(List[ChatCompletionMessageParam], messages),
                    model=model,
                    stream=False,
                    **kwargs,
                )
                next_choice = response.choices[0]
                if next_choice.message.content:
                    yield MessageDeltaEvent(next_choice.message.content)
                if response.usage and (pricing := gpt_pricing(args["model"])):
                    yield UsageEvent.with_pricing(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        pricing=pricing,
                    )

        except openai.BadRequestError as e:
            raise BadRequestError(e.message) from e
        except openai.APIError as e:
            raise CompletionError(e.message) from e


GPT_3_5_TURBO_PRICE_PER_TOKEN: Pricing = {
    "prompt": 0.50 / 1_000_000,
    "response": 1.50 / 1_000_000,
}

GPT_3_5_TURBO_16K_PRICE_PER_TOKEN: Pricing = {
    "prompt": 0.003 / 1000,
    "response": 0.004 / 1000,
}

GPT_4_PRICE_PER_TOKEN: Pricing = {
    "prompt": 30.0 / 1_000_000,
    "response": 60.0 / 1_000_000,
}

GPT_4_TURBO_PRICE_PER_TOKEN: Pricing = {
    "prompt": 10.0 / 1_000_000,
    "response": 30.0 / 1_000_000,
}

GPT_4_32K_PRICE_PER_TOKEN: Pricing = {
    "prompt": 60.0 / 1_000_000,
    "response": 120.0 / 1_000_000,
}

GPT_4_O_2024_05_13_PRICE_PER_TOKEN: Pricing = {
    "prompt": 5.0 / 1_000_000,
    "response": 15.0 / 1_000_000,
}

GPT_4_O_2024_08_06_PRICE_PER_TOKEN: Pricing = {
    "prompt": 2.50 / 1_000_000,
    "response": 10.0 / 1_000_000,
}

GPT_4_O_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 0.150 / 1_000_000,
    "response": 0.600 / 1_000_000,
}

O_1_PREVIEW_PRICE_PER_TOKEN: Pricing = {
    "prompt": 15.0 / 1_000_000,
    "response": 60.0 / 1_000_000,
}

O_1_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 3.0 / 1_000_000,
    "response": 12.0 / 1_000_000,
}


def gpt_pricing(model: str) -> Optional[Pricing]:
    if model.startswith("gpt-3.5-turbo-16k"):
        return GPT_3_5_TURBO_16K_PRICE_PER_TOKEN
    elif model.startswith("gpt-3.5-turbo"):
        return GPT_3_5_TURBO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4-32k"):
        return GPT_4_32K_PRICE_PER_TOKEN
    elif model.startswith("gpt-4o-mini"):
        return GPT_4_O_MINI_PRICE_PER_TOKEN
    elif model.startswith("gpt-4o-2024-05-13") or model.startswith("chatgpt-4o-latest"):
        return GPT_4_O_2024_05_13_PRICE_PER_TOKEN
    elif model.startswith("gpt-4o"):
        return GPT_4_O_2024_08_06_PRICE_PER_TOKEN
    elif model.startswith("gpt-4-turbo") or re.match(r"gpt-4-\d\d\d\d-preview", model):
        return GPT_4_TURBO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4"):
        return GPT_4_PRICE_PER_TOKEN
    elif model.startswith("o1-preview"):
        return O_1_PREVIEW_PRICE_PER_TOKEN
    elif model.startswith("o1-mini"):
        return O_1_MINI_PRICE_PER_TOKEN
    else:
        return None
