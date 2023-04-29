import logging
import os
import signal
import subprocess
from pathlib import Path
import sys
from typing import Iterator, List, Optional

from gptcli.completion import CompletionProvider, Message

LLAMA_DIR: Optional[Path] = None
LLAMA_MODELS: Optional[dict[str, Path]] = None


def init_llama_models(llama_cpp_dir: str, model_paths: dict[str, str]):
    for name, path in model_paths.items():
        if not os.path.isfile(path):
            print(f"LLaMA model {name} not found at {path}.")
            sys.exit(1)
        if not name.startswith("llama"):
            print(f"LLaMA model names must start with `llama`, but got `{name}`.")
            sys.exit(1)

    global LLAMA_DIR, LLAMA_MODELS
    LLAMA_DIR = Path(llama_cpp_dir)
    LLAMA_MODELS = {name: Path(path) for name, path in model_paths.items()}


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
        assert LLAMA_DIR, "LLaMA models not initialized"
        assert LLAMA_MODELS, "LLaMA models not initialized"

        prompt = make_prompt(messages)

        extra_args = []
        if "temperature" in args:
            extra_args += ["--temp", str(args["temperature"])]
        if "top_p" in args:
            extra_args += ["--top_p", str(args["top_p"])]

        process = subprocess.Popen(
            [
                LLAMA_DIR / "main",
                "--model",
                LLAMA_MODELS[args["model"]],
                "-n",
                "4096",
                "-r",
                "### Human:",
                "-p",
                prompt,
                *extra_args,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=True,
        )

        if stream:
            return self._read_stream(process, prompt)
        else:
            return self._read(process, prompt)

    def _read_stream(self, process: subprocess.Popen, prompt: str) -> Iterator[str]:
        assert process.stdout, "LLaMA stdout not set"
        assert process.stderr, "LLaMA stderr not set"

        buffer = ""
        num_read = 0
        char = process.stdout.read(1)

        try:
            while char := process.stdout.read(1):
                num_read += len(char)
                if num_read <= len(prompt):
                    continue

                buffer += char
                if not buffer.startswith("#") or (buffer != END_SEQ[: len(buffer)]):
                    yield buffer
                    buffer = ""
                elif buffer.endswith(END_SEQ):
                    yield buffer[: -len(END_SEQ)]
                    buffer = ""
                    process.terminate()
                    break
        except KeyboardInterrupt:
            os.kill(process.pid, signal.SIGINT)
            raise
        finally:
            process.wait()
            stderr = "".join(process.stderr.readlines())
            logging.debug(f"LLaMA stderr: {stderr}")

    def _read(self, process: subprocess.Popen, prompt: str) -> Iterator[str]:
        result = ""
        for token in self._read_stream(process, prompt):
            result += token
        yield result
