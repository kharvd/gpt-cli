import os
import sys
from typing import Iterator, List, Optional, TypedDict, cast

try:
    from llama_cpp import Completion, CompletionChunk, Llama

    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

from gptcli.completion import CompletionProvider, Message


class LLaMAModelConfig(TypedDict):
    path: str
    human_prompt: str
    assistant_prompt: str


LLAMA_MODELS: Optional[dict[str, LLaMAModelConfig]] = None


def init_llama_models(models: dict[str, LLaMAModelConfig]):
    if not LLAMA_AVAILABLE:
        print(
            "Error: To use llama, you need to install gpt-command-line with the llama optional dependency: pip install gpt-command-line[llama]."
        )
        sys.exit(1)

    for name, model_config in models.items():
        if not os.path.isfile(model_config["path"]):
            print(f"LLaMA model {name} not found at {model_config['path']}.")
            sys.exit(1)
        if not name.startswith("llama"):
            print(f"LLaMA model names must start with `llama`, but got `{name}`.")
            sys.exit(1)

    global LLAMA_MODELS
    LLAMA_MODELS = models


def role_to_name(role: str, model_config: LLaMAModelConfig) -> str:
    if role == "system" or role == "user":
        return model_config["human_prompt"]
    elif role == "assistant":
        return model_config["assistant_prompt"]
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt(messages: List[Message], model_config: LLaMAModelConfig) -> str:
    prompt = "\n".join(
        [
            f"{role_to_name(message['role'], model_config)} {message['content']}"
            for message in messages
        ]
    )
    prompt += f"\n{model_config['assistant_prompt']}"
    return prompt


class LLaMACompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        assert LLAMA_MODELS, "LLaMA models not initialized"

        model_config = LLAMA_MODELS[args["model"]]

        with suppress_stderr():
            llm = Llama(
                model_path=model_config["path"],
                n_ctx=2048,
                verbose=False,
                use_mlock=True,
            )
        prompt = make_prompt(messages, model_config)
        print(prompt)

        extra_args = {}
        if "temperature" in args:
            extra_args["temperature"] = args["temperature"]
        if "top_p" in args:
            extra_args["top_p"] = args["top_p"]

        gen = llm.create_completion(
            prompt,
            max_tokens=1024,
            stop=model_config["human_prompt"],
            stream=stream,
            echo=False,
            **extra_args,
        )
        if stream:
            for x in cast(Iterator[CompletionChunk], gen):
                yield x["choices"][0]["text"]
        else:
            yield cast(Completion, gen)["choices"][0]["text"]


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
