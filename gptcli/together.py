import json
import logging
import os
import requests
import sseclient

from typing import Iterator, List, TypedDict, cast

from gptcli.completion import CompletionProvider, Message

api_key = os.environ.get("TOGETHER_API_KEY")
url = "https://api.together.xyz/inference"


class PromptConfig(TypedDict):
    system_prefix: str
    system_suffix: str
    user_prefix: str
    user_suffix: str
    stop_tokens: List[str]


def build_prompt(messages: List[Message], prompt_config: PromptConfig) -> str:
    prompt = ""
    for message in messages:
        if message["role"] == "system":
            prompt += prompt_config["system_prefix"]
            prompt += message["content"]
            prompt += prompt_config["system_suffix"]
        elif message["role"] == "user":
            prompt += prompt_config["user_prefix"]
            prompt += message["content"]
            prompt += prompt_config["user_suffix"]
        else:
            prompt += message["content"]
    return prompt


class TogetherCompletionProvider(CompletionProvider):
    def __init__(self, prompt_config: PromptConfig):
        self.prompt_config = prompt_config

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]

        assert stream, "Together only supports streaming completions"

        model = args["model"].split("/", 1)[1]
        prompt = build_prompt(messages, self.prompt_config)

        logging.info(f"Prompt: {prompt}")

        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": 2048,
            "stream_tokens": True,
            "stop": self.prompt_config["stop_tokens"],
            **kwargs,
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(url, json=payload, headers=headers, stream=True)
        response.raise_for_status()

        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.data == "[DONE]":
                break

            partial_result = json.loads(event.data)
            token = partial_result["choices"][0]["text"]
            yield token
