from typing import Any, Iterator, List, cast
import openai
import tiktoken

from gptcli.completion import CompletionProvider, Message


class OpenAICompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

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
                if (
                    next_choice["finish_reason"] is None
                    and "content" in next_choice["delta"]
                ):
                    yield next_choice["delta"]["content"]
        else:
            next_choice = response_iter["choices"][0]
            yield next_choice["message"]["content"]


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
