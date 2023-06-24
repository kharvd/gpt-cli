from typing import Iterator, List
import google.generativeai as genai
from gptcli.completion import Completion, CompletionProvider, Message, make_completion


def role_to_author(role: str) -> str:
    if role == "user":
        return "0"
    elif role == "assistant":
        return "1"
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt(messages: List[Message]):
    system_messages = [
        message.get("content") or ""
        for message in messages
        if message["role"] == "system"
    ]
    context = "\n".join(system_messages)
    prompt = [
        {
            "author": role_to_author(message["role"]),
            "content": message.get("content", ""),
        }
        for message in messages
        if message["role"] != "system"
    ]
    return context, prompt


class GoogleCompletionProvider(CompletionProvider):
    def complete(
        self,
        messages: List[Message],
        args: dict,
        stream: bool = False,
        enable_code_execution: bool = False,
    ) -> Iterator[Completion]:
        if enable_code_execution:
            raise ValueError("Code execution is not supported by Google models")

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
        yield make_completion(response.last, finish_reason="stop")
