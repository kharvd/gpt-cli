import os
from pathlib import Path
import sys
from typing import Iterator, List, Optional
from llama_cpp import Llama

from gptcli.completion import CompletionProvider, Message

LLAMA_MODELS: Optional[dict[str, str]] = None


def init_llama_models(model_paths: dict[str, str]):
    for name, path in model_paths.items():
        if not os.path.isfile(path):
            print(f"LLaMA model {name} not found at {path}.")
            sys.exit(1)
        if not name.startswith("llama"):
            print(f"LLaMA model names must start with `llama`, but got `{name}`.")
            sys.exit(1)

    global LLAMA_MODELS
    LLAMA_MODELS = model_paths


def role_to_name(role: str) -> str:
    if role == "system" or role == "user":
        return "### Human: "
    elif role == "assistant":
        return "### Assistant: "
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt(messages: List[Message]) -> str:
    prompt = "\n".join(
        [f"{role_to_name(message['role'])}{message['content']}" for message in messages]
    )
    prompt += "### Assistant:"
    return prompt


END_SEQ = "### Human:"


class LLaMACompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        assert LLAMA_MODELS, "LLaMA models not initialized"

        with suppress_stderr():
            llm = Llama(
                model_path=LLAMA_MODELS[args["model"]],
                n_ctx=2048,
                verbose=False,
                use_mlock=True,
            )
        prompt = make_prompt(messages)

        extra_args = {}
        if "temperature" in args:
            extra_args["temperature"] = args["temperature"]
        if "top_p" in args:
            extra_args["top_p"] = args["top_p"]

        gen = llm.create_completion(
            prompt,
            max_tokens=1024,
            stop=END_SEQ,
            stream=stream,
            echo=False,
            **extra_args,
        )
        if stream:
            for x in gen:
                yield x["choices"][0]["text"]
        else:
            yield gen["choices"][0]["text"]


# https://stackoverflow.com/a/50438156
class suppress_stderr(object):
    def __enter__(self):
        self.errnull_file = open(os.devnull, "w")
        self.old_stderr_fileno_undup = sys.stderr.fileno()
        self.old_stderr_fileno = os.dup(sys.stderr.fileno())
        self.old_stderr = sys.stderr
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stderr = self.old_stderr
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)
        os.close(self.old_stderr_fileno)
        self.errnull_file.close()
