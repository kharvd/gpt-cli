from typing import Any, Iterator, List, cast
import openai

# import tiktoken

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
            functions = FUNCTIONS_SCHEMA
        else:
            functions = []

        response_iter = cast(
            Any,
            openai.ChatCompletion.create(
                messages=messages,
                stream=stream,
                model=args["model"],
                functions=functions,
                **kwargs,
            ),
        )

        if stream:
            for response in response_iter:
                next_choice = response["choices"][0]
                yield next_choice
        else:
            next_choice = response_iter["choices"][0]
            yield next_choice


def num_tokens_from_messages_openai(messages: List[Message], model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        for key, value in message.items():
            assert isinstance(value, str)
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def num_tokens_from_completion_openai(completion: Message, model: str) -> int:
    return num_tokens_from_messages_openai([completion], model)
