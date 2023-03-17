import openai
import os
import argparse
import yaml
import sys
import logging
from blessings import Terminal
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

SYSTEM_PROMPT_DEV = f"You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown. User's `uname`: {os.uname()}"
INIT_USER_PROMPT_DEV = "Your responses must be short and concise. Do not include explanations unless asked."
SYSTEM_PROMPT_GENERAL = "You are a helpful assistant."

ASSISTANT_DEFAULTS = {
    "model": "gpt-3.5-turbo",
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


class ChatSession:
    def __init__(self, assistant):
        self.assistant = assistant
        self.messages = assistant.init_messages()
        self.term = Terminal()
        self.prompt_session = PromptSession()

    def clear(self):
        self.messages = self.assistant.init_messages()
        print(self.term.bold("Cleared the conversation."))

    def rerun(self):
        if len(self.messages) == len(self.assistant.init_messages()):
            print(self.term.bold("Nothing to re-run."))
            return

        self.messages = self.messages[:-1]
        print(self.term.bold("Re-generating the last message."))
        logging.info("Re-generating the last message.")
        self.respond()

    def respond(self, args):
        next_response = []
        try:
            for response in self.assistant.complete_chat(
                self.messages, override_params=args
            ):
                next_response.append(response)
                print(self.term.green(response), end="", flush=True)
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass

        print("\n")
        next_response = {"role": "assistant", "content": "".join(next_response)}
        logging.info(next_response)
        self.messages.append(next_response)

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

    def parse_input(self, input):
        args = {}
        if "--" in input:
            input, *params = input.split(" --")
            for param in params:
                key, value = param.split(" ")
                args[key.strip()] = value.strip()
        return input.strip(), args

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

            user_message = {"role": "user", "content": user_input}
            self.messages.append(user_message)
            logging.info(f"message: {user_message}, args: {args}")
            self.respond(args)


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
        default=config.get("default_assistant", "dev"),
        nargs="?",
        choices=["dev", "general", *config.get("assistants", {}).keys()],
        help="The name of assistant to use. `dev` (default) is a software development assistant, `general` is a generally helpful assistant. You can specify your own assistants in the config file ~/.gptrc. See the README for more information.",
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

    logging.basicConfig(
        filename=args.log_file,
        level=args.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    assistant = init_assistant(args, config.get("assistants", {}))
    logging.info("Starting a new chat session. Assistant config: %s", assistant.config)

    openai.api_key = config.get("api_key", os.environ.get("OPENAI_API_KEY"))
    session = ChatSession(assistant=assistant)
    session.loop()


if __name__ == "__main__":
    main()