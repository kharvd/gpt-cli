import os
from typing import Iterator, List
import anthropic

from gptcli.completion import CompletionProvider, Message

api_key = os.environ.get("ANTHROPIC_API_KEY")


def get_client():
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    return anthropic.Anthropic(api_key=api_key)


def role_to_name(role: str) -> str:
    if role == "system" or role == "user":
        return anthropic.HUMAN_PROMPT
    elif role == "assistant":
        return anthropic.AI_PROMPT
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt(messages: List[Message]) -> str:
    prompt = "\n".join(
        [f"{role_to_name(message['role'])}{message['content']}" for message in messages]
    )
    prompt += f"{role_to_name('assistant')}"
    return prompt


class AnthropicCompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        kwargs = {
            "prompt": make_prompt(messages),
            "stop_sequences": [anthropic.HUMAN_PROMPT],
            "max_tokens_to_sample": 4096,
            "model": args["model"],
        }
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        client = get_client()
        if stream:
            response = client.completions.create(**kwargs, stream=True)
        else:
            response = [client.completions.create(**kwargs, stream=False)]

        for data in response:
            next_completion = data.completion
            yield next_completion


def num_tokens_from_messages_anthropic(messages: List[Message], model: str) -> int:
    prompt = make_prompt(messages)
    client = get_client()
    return client.count_tokens(prompt)


def num_tokens_from_completion_anthropic(message: Message, model: str) -> int:
    client = get_client()
    return client.count_tokens(message["content"])
