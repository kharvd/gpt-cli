#!/usr/bin/env python
from typing import cast
import openai
import os
import argparse
import sys
import logging

from gptcli.assistant import (
    Assistant,
    DEFAULT_ASSISTANTS,
    AssistantGlobalArgs,
    init_assistant,
)
from gptcli.cli import (
    CLIChatListener,
    CLIUserInputProvider,
)
from gptcli.composite import CompositeChatListener
from gptcli.config import GptCliConfig, read_yaml_config
from gptcli.session import ChatSession
from gptcli.shell import execute, simple_response


default_exception_handler = sys.excepthook


def exception_handler(type, value, traceback):
    logging.exception("Uncaught exception", exc_info=(type, value, traceback))
    print("An uncaught exception occurred. Please report this issue on GitHub.")
    default_exception_handler(type, value, traceback)


sys.excepthook = exception_handler


def parse_args(config: GptCliConfig):
    parser = argparse.ArgumentParser(
        description="Run a chat session with ChatGPT. See https://github.com/kharvd/gpt-cli for more information."
    )
    parser.add_argument(
        "assistant_name",
        type=str,
        default=config.default_assistant,
        nargs="?",
        choices=[*DEFAULT_ASSISTANTS.keys(), *config.assistants.keys()],
        help="The name of assistant to use. `general` (default) is a generally helpful assistant, `dev` is a software development assistant with shorter responses. You can specify your own assistants in the config file ~/.gptrc. See the README for more information.",
    )
    parser.add_argument(
        "--no_markdown",
        action="store_false",
        dest="markdown",
        help="Disable markdown formatting in the chat session.",
        default=config.markdown,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="The model to use for the chat session. Overrides the default model defined for the assistant.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="The temperature to use for the chat session. Overrides the default temperature defined for the assistant.",
    )
    parser.add_argument(
        "--top_p",
        type=float,
        default=None,
        help="The top_p to use for the chat session. Overrides the default top_p defined for the assistant.",
    )
    parser.add_argument(
        "--log_file",
        type=str,
        default=config.log_file,
        help="The file to write logs to",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default=config.log_level,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="The log level to use",
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        action="append",
        default=None,
        help="If specified, will not start an interactive chat session and instead will print the response to standard output and exit. May be specified multiple times. Use `-` to read the prompt from standard input. Implies --no_markdown.",
    )
    parser.add_argument(
        "--execute",
        "-e",
        type=str,
        default=None,
        help="If specified, passes the prompt to the assistant and allows the user to edit the produced shell command before executing it. Implies --no_stream. Use `-` to read the prompt from standard input.",
    )
    parser.add_argument(
        "--no_stream",
        action="store_true",
        default=False,
        help="If specified, will not stream the response to standard output. This is useful if you want to use the response in a script. Ignored when the --prompt option is not specified.",
    )

    return parser.parse_args()


def validate_args(args):
    if args.prompt is not None and args.execute is not None:
        print(
            "The --prompt and --execute options are mutually exclusive. Please specify only one of them."
        )
        sys.exit(1)


def main():
    config_path = os.path.expanduser("~/.gptrc")
    config = (
        read_yaml_config(config_path) if os.path.isfile(config_path) else GptCliConfig()
    )
    args = parse_args(config)

    if args.log_file is not None:
        logging.basicConfig(
            filename=args.log_file,
            level=args.log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        # Disable overly verbose logging for markdown_it
        logging.getLogger("markdown_it").setLevel(logging.INFO)

    if config.api_key:
        openai.api_key = config.api_key
    else:
        print(
            "No API key found. Please set the OPENAI_API_KEY environment variable or `api_key: <key>` value in ~/.gptrc"
        )
        sys.exit(1)

    assistant = init_assistant(cast(AssistantGlobalArgs, args), config.assistants)

    if args.prompt is not None:
        run_non_interactive(args, assistant)
    elif args.execute is not None:
        run_execute(args, assistant)
    else:
        run_interactive(args, assistant)


def run_execute(args, assistant):
    logging.info(
        "Starting a non-interactive execution session with prompt '%s'. Assistant config: %s",
    )
    if args.execute == "-":
        args.execute = "".join(sys.stdin.readlines())
    execute(assistant, args.execute)


def run_non_interactive(args, assistant):
    logging.info(
        "Starting a non-interactive session with prompt '%s'. Assistant config: %s",
        args.prompt,
        assistant.config,
    )
    if "-" in args.prompt:
        args.prompt[args.prompt.index("-")] = "".join(sys.stdin.readlines())

    simple_response(assistant, "\n".join(args.prompt), stream=not args.no_stream)


class CLIChatSession(ChatSession):
    def __init__(self, assistant: Assistant, markdown: bool):
        listener = CompositeChatListener(
            [
                CLIChatListener(markdown),
            ]
        )
        super().__init__(assistant, listener)


def run_interactive(args, assistant):
    logging.info("Starting a new chat session. Assistant config: %s", assistant.config)
    session = CLIChatSession(assistant=assistant, markdown=args.markdown)
    input_provider = CLIUserInputProvider()
    session.loop(input_provider)


if __name__ == "__main__":
    main()
