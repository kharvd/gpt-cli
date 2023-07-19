import os
import sys
import random
from typing import Any, Iterator, List, Optional, TypedDict, cast
from typing_extensions import Required

try:
    from llama_cpp import Completion, CompletionChunk, Llama

    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

from gptcli.completion import CompletionProvider, Message


class LLaMAModelConfig(TypedDict, total=False):
    path: Required[str]
    llama2: bool
    n_gpu_layers: int
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
    assert (
        "human_prompt" in model_config and "assistant_prompt" in model_config
    ), "either `llama2: True` or human_prompt and assistant_prompt must be set in the model config"

    if role == "system" or role == "user":
        return model_config["human_prompt"]
    elif role == "assistant":
        return model_config["assistant_prompt"]
    else:
        raise ValueError(f"Unknown role: {role}")


def make_prompt_llama1(messages: List[Message], model_config: LLaMAModelConfig) -> str:
    assert (
        "human_prompt" in model_config and "assistant_prompt" in model_config
    ), "either `llama2: True` or human_prompt and assistant_prompt must be set in the model config"

    prompt = "\n".join(
        [
            f"{role_to_name(message['role'], model_config)} {message['content']}"
            for message in messages
        ]
    )
    prompt += f"\n{model_config['assistant_prompt']}"
    return prompt


B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"
DEFAULT_SYSTEM_PROMPT = """You are a helpful and honest assistant."""


def make_prompt_llama2(llm, messages: List[Message]) -> List[int]:
    if messages[0]["role"] != "system":
        messages = [
            cast(
                Message,
                {
                    "role": "system",
                    "content": DEFAULT_SYSTEM_PROMPT,
                },
            )
        ] + messages
    messages = [
        cast(
            Message,
            {
                "role": messages[1]["role"],
                "content": B_SYS
                + messages[0]["content"]
                + E_SYS
                + messages[1]["content"],
            },
        )
    ] + messages[2:]
    assert all([msg["role"] == "user" for msg in messages[::2]]) and all(
        [msg["role"] == "assistant" for msg in messages[1::2]]
    ), (
        "model only supports 'system', 'user' and 'assistant' roles, "
        "starting with 'system', then 'user' and alternating (u/a/u/a/u...)"
    )

    dialog_tokens = sum(
        [
            llm.tokenize(
                bytes(
                    f"{B_INST} {(prompt['content']).strip()} {E_INST} {(answer['content']).strip()} ",
                    "utf-8",
                ),
                add_bos=True,
            )
            + [llm.token_eos()]
            for prompt, answer in zip(
                messages[::2],
                messages[1::2],
            )
        ],
        [],
    )
    assert (
        messages[-1]["role"] == "user"
    ), f"Last message must be from user, got {messages[-1]['role']}"

    dialog_tokens += llm.tokenize(
        bytes(f"{B_INST} {(messages[-1]['content']).strip()} {E_INST}", "utf-8"),
        add_bos=True,
    )

    return dialog_tokens


llms: dict[str, Any] = {}


class LLaMACompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        assert LLAMA_MODELS, "LLaMA models not initialized"

        model_config = LLAMA_MODELS[args["model"]]

        if model_config.get("llama2", False):
            return self._complete_llama2(model_config, messages, args, stream)
        else:
            return self._complete_llama1(model_config, messages, args, stream)

    def _create_model(self, model_config: LLaMAModelConfig):
        path = model_config["path"]
        if path not in llms:
            with suppress_stderr():
                llms[path] = Llama(
                    model_path=path,
                    n_ctx=4096 if model_config.get("llama2", False) else 2048,
                    verbose=False,
                    use_mlock=True,
                    n_gpu_layers=model_config.get("n_gpu_layers", 0),
                    seed=random.randint(0, 2**32 - 1),
                )
        return llms[path]

    def _complete_llama1(
        self,
        model_config: LLaMAModelConfig,
        messages: List[Message],
        args: dict,
        stream: bool = False,
    ) -> Iterator[str]:
        assert (
            "human_prompt" in model_config and "assistant_prompt" in model_config
        ), "either `llama2: True` or human_prompt and assistant_prompt must be set in the model config"

        llm = self._create_model(model_config)

        prompt = make_prompt_llama1(messages, model_config)

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

    def _complete_llama2(
        self,
        model_config: LLaMAModelConfig,
        messages: List[Message],
        args: dict,
        stream: bool = False,
    ) -> Iterator[str]:
        llm = self._create_model(model_config)

        prompt = make_prompt_llama2(llm, messages)

        extra_args = {}
        if "temperature" in args:
            extra_args["temp"] = args["temperature"]
        if "top_p" in args:
            extra_args["top_p"] = args["top_p"]

        gen = llm.generate(
            prompt,
            top_k=65536,
            **extra_args,
        )

        result = ""
        for token in gen:
            if token == llm.token_eos():
                break

            text = llm.detokenize([token]).decode("utf-8")
            result += text
            if stream:
                yield text

        if not stream:
            yield result


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
