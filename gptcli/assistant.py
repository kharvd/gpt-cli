import os
from attr import dataclass
import openai

from typing import Iterator, TypedDict, List

SYSTEM_PROMPT_DEV = f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown with a correct language tag. User's `uname`: {os.uname()}"
INIT_USER_PROMPT_DEV = "Your responses must be short and concise. Do not include explanations unless asked."
SYSTEM_PROMPT_GENERAL = "You are a helpful assistant."


class Message(TypedDict):
    role: str
    content: str


class ModelOverrides(TypedDict):
    model: str
    temperature: float
    top_p: float


@dataclass
class AssistantConfig:
    messages: List[Message]
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    top_p: float = 1.0


DEFAULT_ASSISTANTS = {
    "dev": AssistantConfig(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_DEV},
            {"role": "user", "content": INIT_USER_PROMPT_DEV},
        ],
    ),
    "general": AssistantConfig(
        messages=[{"role": "system", "content": SYSTEM_PROMPT_GENERAL}],
    ),
}


class Assistant:
    def __init__(self, config: AssistantConfig):
        self.config = config

    def init_messages(self) -> List[Message]:
        return self.config.messages[:]

    def supported_overrides(self) -> List[str]:
        return ["model", "temperature", "top_p"]

    def complete_chat(
        self, messages, override_params: ModelOverrides = {}
    ) -> Iterator[str]:
        response_iter = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            model=override_params.get("model", self.config.model),
            temperature=float(
                override_params.get("temperature", self.config.temperature)
            ),
            top_p=float(override_params.get("top_p", self.config.top_p)),
        )

        # Now iterate over the response iterator to yield the next response
        for response in response_iter:
            next_choice = response["choices"][0]
            if (
                next_choice["finish_reason"] is None
                and "content" in next_choice["delta"]
            ):
                yield next_choice["delta"]["content"]
