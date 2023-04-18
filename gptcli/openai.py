import logging
from typing import List
from rich.console import Console
import tiktoken

from gptcli.assistant import Assistant, Message, ModelOverrides
from gptcli.session import ChatListener

PRICE_PER_TOKEN = {
    "gpt-3.5-turbo": {
        "prompt": 0.002 / 1000,
        "response": 0.002 / 1000,
    },
    "gpt-4": {
        "prompt": 0.03 / 1000,
        "response": 0.06 / 1000,
    }
}

def num_tokens_from_messages(messages: List[Message], model):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            assert isinstance(value, str)
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def price_for_completion(messages: List[Message], response: Message, model: str):
    num_tokens_prompt = num_tokens_from_messages(messages, model)
    num_tokens_response = num_tokens_from_messages([response], model)
    return PRICE_PER_TOKEN[model]["prompt"] * num_tokens_prompt + PRICE_PER_TOKEN[model]["response"] * num_tokens_response


class PriceChatListener(ChatListener):
    def __init__(self, assistant: Assistant):
        self.assistant = assistant
        self.current_spend = 0
        self.logger = logging.getLogger("gptcli-price")
        self.console = Console()

    def on_chat_clear(self):
        self.current_spend = 0

    def on_chat_response(self, messages: List[Message], response: Message, args: ModelOverrides):
        model = self.assistant._param("model", args)
        num_tokens = num_tokens_from_messages(messages + [response], model)
        price = price_for_completion(messages, response, model)
        self.current_spend += price
        self.logger.info(f"Token usage {num_tokens}")
        self.logger.info(f"Message price (model: {model}): ${price:.3f}")
        self.logger.info(f"Current spend: ${self.current_spend:.3f}")
        self.console.print(
            f"Tokens: {num_tokens} | Price: ${price:.3f} | Total: ${self.current_spend:.3f}", justify="right", style="dim"
        )
