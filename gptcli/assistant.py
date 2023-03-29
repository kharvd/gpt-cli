import os
import openai

from typing import Iterator, Optional, TypedDict, List


class Message(TypedDict):
    role: str
    content: str


class ModelOverrides(TypedDict):
    model: str
    temperature: float
    top_p: float


class AssistantConfig(TypedDict):
    messages: Optional[List[Message]]
    model: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]


CONFIG_DEFAULTS = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1.0,
}

DEFAULT_ASSISTANTS = {
    "dev": {
        "messages": [
            {
                "role": "system",
                "content": f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown with a correct language tag. User's `uname`: {os.uname()}",
            },
            {
                "role": "user",
                "content": "Your responses must be short and concise. Do not include explanations unless asked.",
            },
        ],
    },
    "general": {
        "messages": [{"role": "system", "content": "You are a helpful assistant."}],
    },
    "bash": {
        "messages": [
            {
                "role": "system",
                "content": f"You output only valid and correct shell commands according to the user's prompt. You don't provide any explanations or any other text that is not valid shell commands. User's `uname`: {os.uname()}. User's `$SHELL`: {os.environ.get('SHELL')}.",
            }
        ],
    },
}


class Assistant:
    def __init__(self, config: AssistantConfig):
        self.config = config

    @classmethod
    def from_config(cls, name: str, config: AssistantConfig):
        if name in DEFAULT_ASSISTANTS:
            # Merge the config with the default config
            # If a key is in both, use the value from the config
            default_config = DEFAULT_ASSISTANTS[name]
            for key in [*config.keys(), *default_config.keys()]:
                if config.get(key) is None:
                    config[key] = default_config[key]

        return cls(config)

    def init_messages(self) -> List[Message]:
        return self.config["messages"][:]

    def supported_overrides(self) -> List[str]:
        return ["model", "temperature", "top_p"]

    def _param(self, param: str, override_params: ModelOverrides) -> float:
        # If the param is in the override_params, use that value
        # Otherwise, use the value from the config
        # Otherwise, use the default value
        return override_params.get(
            param, self.config.get(param, CONFIG_DEFAULTS[param])
        )

    def complete_chat(
        self, messages, override_params: ModelOverrides = {}, stream: bool = True
    ) -> Iterator[str]:
        response_iter = openai.ChatCompletion.create(
            messages=messages,
            stream=stream,
            model=self._param("model", override_params),
            temperature=float(self._param("temperature", override_params)),
            top_p=float(self._param("top_p", override_params)),
        )

        if stream:
            for response in response_iter:
                next_choice = response["choices"][0]
                if (
                    next_choice["finish_reason"] is None
                    and "content" in next_choice["delta"]
                ):
                    yield next_choice["delta"]["content"]
        else:
            next_choice = response_iter["choices"][0]
            yield next_choice["message"]["content"]
