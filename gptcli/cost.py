from gptcli.anthropic import (
    num_tokens_from_completion_anthropic,
    num_tokens_from_messages_anthropic,
)
from gptcli.assistant import Assistant
from gptcli.completion import Message, ModelOverrides
from gptcli.openai import (
    num_tokens_from_completion_openai,
    num_tokens_from_messages_openai,
)
from gptcli.session import ChatListener


from rich.console import Console


import logging
from typing import List


def num_tokens_from_messages(messages: List[Message], model: str) -> int:
    if model.startswith("gpt"):
        return num_tokens_from_messages_openai(messages, model)
    elif model.startswith("claude"):
        return num_tokens_from_messages_anthropic(messages, model)
    elif model.startswith("llama"):
        return 0
    else:
        raise ValueError(f"Unknown model: {model}")


def num_tokens_from_completion(message: Message, model: str) -> int:
    if model.startswith("gpt"):
        return num_tokens_from_completion_openai(message, model)
    elif model.startswith("claude"):
        return num_tokens_from_completion_anthropic(message, model)
    elif model.startswith("llama"):
        return 0
    else:
        raise ValueError(f"Unknown model: {model}")


GPT_3_5_TURBO_PRICE_PER_TOKEN = {
    "prompt": 0.002 / 1000,
    "response": 0.002 / 1000,
}

GPT_4_PRICE_PER_TOKEN = {
    "prompt": 0.03 / 1000,
    "response": 0.06 / 1000,
}

GPT_4_32K_PRICE_PER_TOKEN = {
    "prompt": 0.06 / 1000,
    "response": 0.12 / 1000,
}

CLAUDE_V1_PRICE_PER_TOKEN = {
    "prompt": 11.02 / 1_000_000,
    "response": 32.68 / 1_000_000,
}

CLAUDE_INSTANT_V1_PRICE_PER_TOKEN = {
    "prompt": 1.63 / 1_000_000,
    "response": 5.51 / 1_000_000,
}

PRICE_PER_TOKEN = {
    "gpt-3.5-turbo": GPT_3_5_TURBO_PRICE_PER_TOKEN,
    "gpt-3.5-turbo-0301": GPT_3_5_TURBO_PRICE_PER_TOKEN,
    "gpt-4": GPT_4_PRICE_PER_TOKEN,
    "gpt-4-0314": GPT_4_PRICE_PER_TOKEN,
    "gpt-4-32k": GPT_4_32K_PRICE_PER_TOKEN,
    "gpt-4-32k-0314": GPT_4_32K_PRICE_PER_TOKEN,
    "claude-v1": CLAUDE_V1_PRICE_PER_TOKEN,
    "claude-v1-100k": CLAUDE_V1_PRICE_PER_TOKEN,
    "claude-v1.0": CLAUDE_V1_PRICE_PER_TOKEN,
    "claude-v1.2": CLAUDE_V1_PRICE_PER_TOKEN,
    "claude-v1.3": CLAUDE_V1_PRICE_PER_TOKEN,
    "claude-instant-v1": CLAUDE_INSTANT_V1_PRICE_PER_TOKEN,
    "claude-instant-v1-100k": CLAUDE_INSTANT_V1_PRICE_PER_TOKEN,
    "claude-instant-v1.0": CLAUDE_INSTANT_V1_PRICE_PER_TOKEN,
    "llama": {
        "prompt": 0,
        "response": 0,
    },
}


def price_for_completion(messages: List[Message], response: Message, model: str):
    num_tokens_prompt = num_tokens_from_messages(messages, model)
    num_tokens_response = num_tokens_from_completion(response, model)
    return (
        PRICE_PER_TOKEN[model]["prompt"] * num_tokens_prompt
        + PRICE_PER_TOKEN[model]["response"] * num_tokens_response
    )


class PriceChatListener(ChatListener):
    def __init__(self, assistant: Assistant):
        self.assistant = assistant
        self.current_spend = 0
        self.logger = logging.getLogger("gptcli-price")
        self.console = Console()

    def on_chat_clear(self):
        self.current_spend = 0

    def on_chat_response(
        self, messages: List[Message], response: Message, args: ModelOverrides
    ):
        model = self.assistant._param("model", args)
        num_tokens = num_tokens_from_messages(messages + [response], model)
        price = price_for_completion(messages, response, model)
        self.current_spend += price
        self.logger.info(f"Token usage {num_tokens}")
        self.logger.info(f"Message price (model: {model}): ${price:.3f}")
        self.logger.info(f"Current spend: ${self.current_spend:.3f}")
        self.console.print(
            f"Tokens: {num_tokens} | Price: ${price:.3f} | Total: ${self.current_spend:.3f}",
            justify="right",
            style="dim",
        )
