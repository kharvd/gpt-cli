import re
from typing import Iterator, List, Optional, cast
import openai
from openai import OpenAI
from openai.types.responses import ResponseInputParam

from gptcli.completion import (
    CompletionEvent,
    CompletionProvider,
    Message,
    CompletionError,
    BadRequestError,
    MessageDeltaEvent,
    Pricing,
    ThinkingDeltaEvent,
    ToolCallEvent,
    UsageEvent,
)


def is_reasoning_model(model: str) -> bool:
    return model.startswith("o1") or model.startswith("o3") or model.startswith("o4")


class OpenAICompletionProvider(CompletionProvider):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.client = OpenAI(
            api_key=api_key or openai.api_key, base_url=base_url or openai.base_url
        )

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        model = args["model"]
        if model.startswith("oai-compat:"):
            model = model[len("oai-compat:") :]

        if model.startswith("oai-azure:"):
            model = model[len("oai-azure:") :]

        kwargs = {}
        is_reasoning = is_reasoning_model(args["model"])
        if "temperature" in args and not is_reasoning:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args and not is_reasoning:
            kwargs["top_p"] = args["top_p"]
        if is_reasoning:
            kwargs["reasoning"] = {"effort": "high", "summary": "auto"}
            kwargs["tools"] = [
                {"type": "web_search_preview"}
            ]  # provide reasoning models with search capabilities

        try:
            if stream:
                response_iter = self.client.responses.create(
                    model=model,
                    input=cast(ResponseInputParam, messages),
                    stream=True,
                    store=False,
                    **kwargs,
                )

                for response in response_iter:
                    if response.type == "response.output_text.delta":
                        yield MessageDeltaEvent(response.delta)
                    elif response.type == "response.reasoning_summary_text.delta":
                        yield ThinkingDeltaEvent(response.delta)
                    elif response.type == "response.reasoning_summary_part.done":
                        yield ThinkingDeltaEvent("\n\n")
                    elif response.type == "response.web_search_call.in_progress":
                        yield ToolCallEvent("Searching the web...")
                    elif response.type == "response.completed" and (
                        pricing := gpt_pricing(args["model"])
                    ):
                        if response.response.usage:
                            yield UsageEvent.with_pricing(
                                prompt_tokens=response.response.usage.input_tokens,
                                completion_tokens=response.response.usage.output_tokens,
                                total_tokens=response.response.usage.input_tokens
                                + response.response.usage.output_tokens,
                                pricing=pricing,
                            )
            else:
                response = self.client.responses.create(
                    model=model,
                    input=cast(ResponseInputParam, messages),
                    stream=False,
                    store=False,
                    **kwargs,
                )

                yield MessageDeltaEvent(response.output_text)

                if response.usage and (pricing := gpt_pricing(args["model"])):
                    yield UsageEvent.with_pricing(
                        prompt_tokens=response.usage.input_tokens,
                        completion_tokens=response.usage.output_tokens,
                        total_tokens=response.usage.input_tokens
                        + response.usage.output_tokens,
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

GPT_4_1_PRICE_PER_TOKEN: Pricing = {
    "prompt": 2.0 / 1_000_000,
    "response": 8.0 / 1_000_000,
}

GPT_4_1_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 0.400 / 1_000_000,
    "response": 1.600 / 1_000_000,
}

GPT_4_1_NANO_PRICE_PER_TOKEN: Pricing = {
    "prompt": 0.1 / 1_000_000,
    "response": 0.4 / 1_000_000,
}

GPT_4_5_PRICE_PER_TOKEN: Pricing = {
    "prompt": 75.0 / 1_000_000,
    "response": 150.0 / 1_000_000,
}

O_1_PRO_PRICE_PER_TOKEN: Pricing = {
    "prompt": 150.0 / 1_000_000,
    "response": 600.0 / 1_000_000,
}

O_1_PRICE_PER_TOKEN: Pricing = {
    "prompt": 15.0 / 1_000_000,
    "response": 60.0 / 1_000_000,
}

O_1_PREVIEW_PRICE_PER_TOKEN: Pricing = {
    "prompt": 15.0 / 1_000_000,
    "response": 60.0 / 1_000_000,
}

O_1_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 3.0 / 1_000_000,
    "response": 12.0 / 1_000_000,
}

O_3_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 1.1 / 1_000_000,
    "response": 4.4 / 1_000_000,
}

O_3_PRICE_PER_TOKEN: Pricing = {
    "prompt": 10.0 / 1_000_000,
    "response": 40.0 / 1_000_000,
}

O_4_MINI_PRICE_PER_TOKEN: Pricing = {
    "prompt": 1.1 / 1_000_000,
    "response": 4.4 / 1_000_000,
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
    elif model.startswith("gpt-4.1-mini"):
        return GPT_4_1_MINI_PRICE_PER_TOKEN
    elif model.startswith("gpt-4.1-nano"):
        return GPT_4_1_NANO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4.1"):
        return GPT_4_1_PRICE_PER_TOKEN
    elif model.startswith("gpt-4.5"):
        return GPT_4_5_PRICE_PER_TOKEN
    elif model.startswith("gpt-4-turbo") or re.match(r"gpt-4-\d\d\d\d-preview", model):
        return GPT_4_TURBO_PRICE_PER_TOKEN
    elif model.startswith("gpt-4"):
        return GPT_4_PRICE_PER_TOKEN
    elif model.startswith("o1-pro"):
        return O_1_PRO_PRICE_PER_TOKEN
    elif model.startswith("o1-preview"):
        return O_1_PREVIEW_PRICE_PER_TOKEN
    elif model.startswith("o1-mini"):
        return O_1_MINI_PRICE_PER_TOKEN
    elif model.startswith("o1"):
        return O_1_PRICE_PER_TOKEN
    elif model.startswith("o3-mini"):
        return O_3_MINI_PRICE_PER_TOKEN
    elif model.startswith("o3"):
        return O_3_PRICE_PER_TOKEN
    elif model.startswith("o4-mini"):
        return O_4_MINI_PRICE_PER_TOKEN
    else:
        return None
