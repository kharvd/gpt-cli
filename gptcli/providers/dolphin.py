import os
import sys
from typing import Dict, Iterator, List, Optional, TypedDict, cast
import requests

class DolphinModelConfig(TypedDict):
    path: str
    human_prompt: str
    assistant_prompt: str

DOLPHIN_MODELS: Optional[dict[str, DolphinModelConfig]] = None

def init_dolphin_models(models: dict[str, DolphinModelConfig]):
    global DOLPHIN_MODELS
    DOLPHIN_MODELS = models

def role_to_name(role: str, model_config: DolphinModelConfig) -> str:
    if role == "system" or role == "user":
        return model_config["human_prompt"]
    elif role == "assistant":
        return model_config["assistant_prompt"]
    else:
        raise ValueError(f"Unknown role: {role}")

def make_prompt(messages: List[dict], model_config: DolphinModelConfig) -> str:
    prompt = "\n".join(
        [
            f"{role_to_name(message['role'], model_config)} {message['content']}"
            for message in messages
        ]
    )
    prompt += f"\n{model_config['assistant_prompt']}"
    return prompt

class DolphinCompletionProvider():

    def complete(
        self, messages: List[dict], args: dict, stream: bool = False
    ) -> Iterator[str]:
        model_config: Optional[Dict[str, DolphinModelConfig]] = {
            "path": "/home/juan/dolphin-2.7-mixtral-8x7b.Q4_K_M.gguf",
            "human_prompt": "Human",
            "assistant_prompt": "Assistant",
        }

        gpu = "dfa" in args["model"]

        if (gpu):
            #SERVICE_URL = "https://cave.keychaotic.com:6102"
            SERVICE_URL = "https://cave.keychaotic.com:6102"
        else:
            SERVICE_URL = "https://cave.keychaotic.com:6102"
            #SERVICE_URL = "http://192.168.1.85:6101"

        prompt = make_prompt(messages, model_config)
        #print(model_config)

        payload = {
            "messages": messages,
            "stream": stream,
        }
        if "temperature" in args:
            payload["temperature"] = args["temperature"]
        if "top_p" in args:
            payload["top_p"] = args["top_p"]

        #print("attempting " + SERVICE_URL + "/complete")
        response = requests.post(SERVICE_URL + "/complete", json=payload, stream=stream)#, verify=False)
        #response = requests.post(SERVICE_URL + "/complete", json=payload, stream=stream)
        #response = requests.get('https://cave.keychaotic.com:6102/complete', verify=False)

        if stream:
            for chunk in response.iter_content(chunk_size=None):
                yield chunk.decode("utf-8")
        else:
            completion = response.json()["completion"]
            yield completion
