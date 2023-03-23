import re
import openai
import os
import argparse
import yaml
import sys
import logging
from blessings import Terminal
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from openai import OpenAIError, InvalidRequestError
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown

SYSTEM_PROMPT_DEV = f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown with a correct language tag. User's `uname`: {os.uname()}"
INIT_USER_PROMPT_DEV = "Your responses must be short and concise. Do not include explanations unless asked."
SYSTEM_PROMPT_GENERAL = "You are a helpful assistant."

ASSISTANT_DEFAULTS = {
    "model": "gpt-4",
    "temperature": 0.7,
    "top_p": 1,
}

DEFAULT_ASSISTANTS = {
    "dev": {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_DEV},
            {"role": "user", "content": INIT_USER_PROMPT_DEV},
        ],
    },
    "general": {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT_GENERAL}],
    },
}


class Assistant:
    def __init__(self, **kwargs):
        """
        Initialize an assistant with the given model and temperature.

        :param model: The model to use for the assistant. Defaults to gpt-3.5-turbo.
        :param temperature: The temperature to use for the assistant. Defaults to 0.7.
        :param messages: The initial messages to use for the assistant.
        """
        self.model = kwargs.get("model", ASSISTANT_DEFAULTS["model"])
        self.temperature = kwargs.get("temperature", ASSISTANT_DEFAULTS["temperature"])
        self.top_p = kwargs.get("top_p", ASSISTANT_DEFAULTS["top_p"])
        self.messages = kwargs["messages"]
        self.config = kwargs

    def init_messages(self):
        return self.messages[:]

    def supported_overrides(self):
        return ["model", "temperature", "top_p"]

    def complete_chat(self, messages, override_params={}):
        response_iter = openai.ChatCompletion.create(
            messages=messages,
            stream=True,
            model=override_params.get("model", self.model),
            temperature=float(override_params.get("temperature", self.temperature)),
            top_p=float(override_params.get("top_p", self.top_p)),
        )

        # Now iterate over the response iterator to yield the next response
        for response in response_iter:
            next_choice = response["choices"][0]
            if (
                next_choice["finish_reason"] is None
                and "content" in next_choice["delta"]
            ):
                yield next_choice["delta"]["content"]


TERMINAL_WELCOME = """
Hi! I'm here to help. Type `q` or Ctrl-D to exit, `c` or Ctrl-C to clear
the conversation, `r` or Ctrl-R to re-generate the last response. 
To enter multi-line mode, enter a backslash `\` followed by a new line.
Exit the multi-line mode by pressing ESC and then Enter (Meta+Enter).
"""

COMMAND_CLEAR = ("clear", "c")
COMMAND_QUIT = ("quit", "q")
COMMAND_RERUN = ("rerun", "r")


def stream_print_response(text_iterator, markdown):
    console = Console()
    current_text = ""
    with Live(console=console, auto_refresh=False) as live:
        for next_text in text_iterator:
            current_text += next_text
            if markdown:
                content = Markdown(current_text, style="green")
            else:
                content = Text(current_text, style="green")
            live.update(content)
            live.refresh()
            yield next_text
    console.print()


class ChatSession:
    def __init__(self, assistant, markdown):
        self.assistant = assistant
        self.messages = assistant.init_messages()
        self.user_prompts = []
        self.term = Terminal()
        self.prompt_session = PromptSession()
        self.markdown = markdown

    def clear(self):
        self.messages = self.assistant.init_messages()
        print(self.term.bold("Cleared the conversation."))

    def rerun(self):
        if len(self.user_prompts) == 0:
            print(self.term.bold("Nothing to re-run."))
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        print(self.term.bold("Re-generating the last message."))
        logging.info("Re-generating the last message.")
        _, args = self.user_prompts[-1]
        self.respond(args)

    def respond(self, args):
        next_response = []
        try:
            completion_iter = self.assistant.complete_chat(
                self.messages, override_params=args
            )
            for response in stream_print_response(completion_iter, self.markdown):
                next_response.append(response)
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass
        except InvalidRequestError as e:
            print(
                self.term.red(
                    f"Request Error. The last prompt was not saved: {type(e)}: {e}"
                )
            )
            logging.exception(e)
            return False
        except OpenAIError as e:
            print(
                self.term.red(
                    f"API Error. Type `r` or Ctrl-R to try again: {type(e)}: {e}"
                )
            )
            logging.exception(e)
            return True

        next_response = {"role": "assistant", "content": "".join(next_response)}
        logging.info(next_response)
        self.messages.append(next_response)
        return True

    def prompt(self, multiline=False):
        bindings = KeyBindings()

        @bindings.add("c-c")
        def _ctrl_c(event):
            if len(event.current_buffer.text) == 0 and not multiline:
                event.current_buffer.text = COMMAND_CLEAR[0]
                event.current_buffer.validate_and_handle()
            else:
                event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

        @bindings.add("c-d")
        def _ctrl_d(event):
            if len(event.current_buffer.text) == 0:
                if not multiline:
                    event.current_buffer.text = COMMAND_QUIT[0]
                event.current_buffer.validate_and_handle()

        @bindings.add("c-r")
        def _ctrl_r(event):
            if len(event.current_buffer.text) == 0:
                event.current_buffer.text = COMMAND_RERUN[0]
                event.current_buffer.validate_and_handle()

        try:
            return self.prompt_session.prompt(
                "> " if not multiline else "multiline> ",
                vi_mode=True,
                multiline=multiline,
                enable_open_in_editor=True,
                key_bindings=bindings,
            )
        except KeyboardInterrupt:
            return ""

    def request_input(self):
        line = self.prompt()

        if line != "\\":
            return line

        return self.prompt(multiline=True)

    def _validate_args(self, args):
        for key in args:
            if key not in self.assistant.supported_overrides():
                msg = self.term.red(
                    f"Invalid argument: {key}. Allowed arguments: {self.assistant.supported_overrides()}"
                )
                print(msg)
                return False
        return True

    def parse_input(self, input):
        args = {}
        regex = r"--(\w+)(?:\s+|=)([^\s]+)"
        matches = re.findall(regex, input)
        if matches:
            args = dict(matches)
            if not self._validate_args(args):
                return None, {}

            input = input.split("--")[0].strip()

        return input, args

    def loop(self):
        print(self.term.bold(TERMINAL_WELCOME))

        while True:
            while (next_user_input := self.request_input()) == "":
                pass

            if next_user_input in COMMAND_QUIT:
                break

            if next_user_input in COMMAND_CLEAR:
                self.clear()
                logging.info("Cleared the conversation.")
                continue

            if next_user_input in COMMAND_RERUN:
                self.rerun()
                continue

            user_input, args = self.parse_input(next_user_input)
            if user_input is None:
                continue

            if args:
                print(self.term.bold_yellow(f"Running model with: {args}"))

            user_message = {"role": "user", "content": user_input}
            logging.info(f"message: {user_message}, args: {args}")
            self.messages.append(user_message)
            self.user_prompts.append((user_message, args))
            if not self.respond(args):
                # Roll back the last user message
                self.messages = self.messages[:-1]
                self.user_prompts = self.user_prompts[:-1]


def read_yaml_config(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


default_exception_handler = sys.excepthook


def exception_handler(type, value, traceback):
    logging.exception("Uncaught exception", exc_info=(type, value, traceback))
    print("An uncaught exception occurred. Please report this issue on GitHub.")
    default_exception_handler(type, value, traceback)


sys.excepthook = exception_handler


def init_assistant(args, custom_assistants):
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
    parser = argparse.ArgumentParser(description="Run a chat session with ChatGPT.")
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
