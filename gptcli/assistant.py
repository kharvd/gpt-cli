import os
import openai

from typing import Iterator, TypedDict, List

SYSTEM_PROMPT_DEV = f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown with a correct language tag. User's `uname`: {os.uname()}"
INIT_USER_PROMPT_DEV = "Your responses must be short and concise. Do not include explanations unless asked."
SYSTEM_PROMPT_GENERAL = "You are a helpful assistant."

ASSISTANT_DEFAULTS = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1,
}

DEFAULT_ASSISTANTS = {
    "dev": {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_DEV},
            {"role": "user", "content": INIT_USER_PROMPT_DEV},
        ],
    },
    "general": {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT_GENERAL}],
    },
}


class Message(TypedDict):
    role: str
    content: str


class ModelOverrides(TypedDict):
    model: str
    temperature: float
    top_p: float


class Assistant:
    def __init__(self, **kwargs):
        """
        Initialize an assistant with the given model and temperature.

        :param model: The model to use for the assistant. Defaults to gpt-3.5-turbo.
        :param temperature: The temperature to use for the assistant. Defaults to 0.7.
        :param messages: The initial messages to use for the assistant.
        """
        self.model = kwargs.get("model", ASSISTANT_DEFAULTS["model"])
        self.temperature = kwargs.get("temperature", ASSISTANT_DEFAULTS["temperature"])
        self.top_p = kwargs.get("top_p", ASSISTANT_DEFAULTS["top_p"])
        self.messages: List[Message] = kwargs["messages"]
        self.config = kwargs

    def init_messages(self) -> List[Message]:
        return self.messages[:]

    def supported_overrides(self) -> List[str]:
        return ["model", "temperature", "top_p"]

    def complete_chat(
        self, messages, override_params: ModelOverrides = {}
    ) -> Iterator[str]:
        response_iter = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            model=override_params.get("model", self.model),
            temperature=float(override_params.get("temperature", self.temperature)),
            top_p=float(override_params.get("top_p", self.top_p)),
        )

        # Now iterate over the response iterator to yield the next response
        for response in response_iter:
            next_choice = response["choices"][0]
            if (
                next_choice["finish_reason"] is None
                and "content" in next_choice["delta"]
            ):
                yield next_choice["delta"]["content"]
