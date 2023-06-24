import logging
from typing import Any, Iterator, List, cast
import openai
import tiktoken

from gptcli.completion import Completion, CompletionProvider, Message

FUNCTIONS_SCHEMA = [
    {
        "name": "python_eval",
        "description": "Evaluate an arbitrary Python snippet",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The Python code to evaluate",
                },
            },
            "required": ["source"],
        },
    },
    {
        "name": "pip_install",
        "description": "Install a Python package. The kernel will be restarted automatically after the package is installed.",
        "parameters": {
            "type": "object",
            "properties": {
                "package": {
                    "type": "string",
                    "description": "The package to install",
                },
            },
            "required": ["package"],
        },
    },
]


class OpenAICompletionProvider(CompletionProvider):
    def complete(
        self,
        messages: List[Message],
        args: dict,
        stream: bool = False,
        enable_code_execution: bool = False,
    ) -> Iterator[Completion]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        if enable_code_execution:
            kwargs["functions"] = FUNCTIONS_SCHEMA

        response_iter = cast(
            Any,
            openai.ChatCompletion.create(
                messages=messages,
                stream=stream,
                model=args["model"],
                **kwargs,
            ),
        )

        if stream:
            for response in response_iter:
                next_choice = response["choices"][0]
                yield next_choice
        else:
            next_choice = response_iter["choices"][0]
            next_choice["delta"] = next_choice["message"]
            yield next_choice


def num_tokens_from_messages_openai(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        return num_tokens_from_messages_openai(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        return num_tokens_from_messages_openai(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            logging.debug(f"key: {key}, value: {value}")
            if key == "function_call":
                # TODO: is this correct?
                value = f"{value['name']}({value['arguments']})"
            if key == "content":
                # TODO: content is None for some messages with function calls
                if value is None:
                    continue
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def num_tokens_from_completion_openai(completion: Message, model: str) -> int:
    return num_tokens_from_messages_openai([completion], model)
