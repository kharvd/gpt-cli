import openai
import os
import argparse
import yaml
import sys
import logging

from gptcli.assistant import Assistant, DEFAULT_ASSISTANTS
from gptcli.cli import ChatSession


def read_yaml_config(file_path: str):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


default_exception_handler = sys.excepthook


def exception_handler(type, value, traceback):
    logging.exception("Uncaught exception", exc_info=(type, value, traceback))
    print("An uncaught exception occurred. Please report this issue on GitHub.")
    default_exception_handler(type, value, traceback)


sys.excepthook = exception_handler


def init_assistant(args, custom_assistants) -> Assistant:
    all_assistants = {**DEFAULT_ASSISTANTS, **custom_assistants}
    assistant_config = all_assistants[args.assistant_name]
    if args.temperature is not None:
        assistant_config["temperature"] = args.temperature
    if args.model is not None:
        assistant_config["model"] = args.model
    if args.top_p is not None:
        assistant_config["top_p"] = args.top_p
    return Assistant(**assistant_config)


def parse_args(config):
    parser = argparse.ArgumentParser(
        description="Run a chat session with ChatGPT. See https://github.com/kharvd/gpt-cli for more information."
    )
    parser.add_argument(
        "assistant_name",
        type=str,
        default=config.get("default_assistant", "general"),
        nargs="?",
        choices=["dev", "general", *config.get("assistants", {}).keys()],
        help="The name of assistant to use. `general` (default) is a generally helpful assistant, `dev` is a software development assistant with shorter responses. You can specify your own assistants in the config file ~/.gptrc. See the README for more information.",
    )
    parser.add_argument(
        "--no_markdown",
        action="store_false",
        dest="markdown",
        help="Disable markdown formatting in the chat session.",
        default=config.get("markdown", True),
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
        default=config.get("log_file", None),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default=config.get("log_level", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=argparse.SUPPRESS,
    )

    return parser.parse_args()


def main():
    config_path = os.path.expanduser("~/.gptrc")
    config = read_yaml_config(config_path) if os.path.isfile(config_path) else {}
    args = parse_args(config)

    if args.log_file is not None:
        logging.basicConfig(
            filename=args.log_file,
            level=args.log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        # Disable overly verbose logging for markdown_it
        logging.getLogger("markdown_it").setLevel(logging.INFO)

    assistant = init_assistant(args, config.get("assistants", {}))
    logging.info("Starting a new chat session. Assistant config: %s", assistant.config)

    openai.api_key = config.get("api_key", os.environ.get("OPENAI_API_KEY"))
    session = ChatSession(assistant=assistant, markdown=args.markdown)
    session.loop()


if __name__ == "__main__":
    main()
