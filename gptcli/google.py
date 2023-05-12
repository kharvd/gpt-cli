from typing import Iterator, List
import google.generativeai as genai
from gptcli.completion import CompletionProvider, Message


def role_to_author(role: str) -> str:
    if role == "user":
        return "0"
    elif role == "assistant":
        return "1"
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt(messages: List[Message]):
    system_messages = [
        message["content"] for message in messages if message["role"] == "system"
    ]
    context = "\n".join(system_messages)
    prompt = [
        {"author": role_to_author(message["role"]), "content": message["content"]}
        for message in messages
        if message["role"] != "system"
    ]
    return context, prompt


class GoogleCompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        context, prompt = make_prompt(messages)
        kwargs = {
            "context": context,
            "messages": prompt,
        }
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        response = genai.chat(**kwargs)
        yield response.last
