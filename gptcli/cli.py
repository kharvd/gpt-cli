from contextlib import contextmanager
import re
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from openai import OpenAIError, InvalidRequestError
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .assistant import Assistant, ModelOverrides


TERMINAL_WELCOME = """
Hi! I'm here to help. Type `q` or Ctrl-D to exit, `c` or Ctrl-C to clear
the conversation, `r` or Ctrl-R to re-generate the last response. 
To enter multi-line mode, enter a backslash `\` followed by a new line.
Exit the multi-line mode by pressing ESC and then Enter (Meta+Enter).
"""

COMMAND_CLEAR = ("clear", "c")
COMMAND_QUIT = ("quit", "q")
COMMAND_RERUN = ("rerun", "r")


class StreamingMarkdownPrinter:
    def __init__(self, console: Console, markdown: bool):
        self.console = console
        self.current_text = ""
        self.markdown = markdown
        self.live: Optional[Live] = None

    def __enter__(self):
        self.live = Live(console=self.console, auto_refresh=False)
        self.live.__enter__()
        return self

    def print(self, text: str):
        self.current_text += text
        if self.markdown:
            content = Markdown(self.current_text, style="green")
        else:
            content = Text(self.current_text, style="green")
        self.live.update(content)
        self.live.refresh()

    def __exit__(self, *args):
        self.live.__exit__(*args)
        self.console.print()


def prompt(session: PromptSession[str], multiline=False):
    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event: KeyPressEvent):
        if len(event.current_buffer.text) == 0 and not multiline:
            event.current_buffer.text = COMMAND_CLEAR[0]
            event.current_buffer.validate_and_handle()
        else:
            event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @bindings.add("c-d")
    def _(event: KeyPressEvent):
        if len(event.current_buffer.text) == 0:
            if not multiline:
                event.current_buffer.text = COMMAND_QUIT[0]
            event.current_buffer.validate_and_handle()

    @bindings.add("c-r")
    def _(event: KeyPressEvent):
        if len(event.current_buffer.text) == 0:
            event.current_buffer.text = COMMAND_RERUN[0]
            event.current_buffer.validate_and_handle()

    try:
        return session.prompt(
            "> " if not multiline else "multiline> ",
            vi_mode=True,
            multiline=multiline,
            enable_open_in_editor=True,
            key_bindings=bindings,
        )
    except KeyboardInterrupt:
        return ""


class ChatSession:
    def __init__(self, assistant: Assistant, markdown: bool):
        self.assistant = assistant
        self.messages = assistant.init_messages()
        self.user_prompts: List[Tuple[str, ModelOverrides]] = []
        self.prompt_session = PromptSession[str]()
        self.markdown = markdown
        self.console = Console()

    def clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        self.console.print("[bold]Cleared the conversation.[/bold]")

    def rerun(self):
        if len(self.user_prompts) == 0:
            self.console.print("[bold]Nothing to re-run.[/bold]")
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        self.console.print("[bold]Re-running the last message.[/bold]")
        logging.info("Re-generating the last message.")
        _, args = self.user_prompts[-1]
        self.respond(args)

    def respond(self, args: ModelOverrides):
        next_response = ""
        try:
            completion_iter = self.assistant.complete_chat(
                self.messages, override_params=args
            )

            with StreamingMarkdownPrinter(self.console, self.markdown) as stream:
                for response in completion_iter:
                    next_response += response
                    stream.print(response)
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass
        except InvalidRequestError as e:
            self.console.print(
                f"[red]Request Error. The last prompt was not saved: {type(e)}: {e}[/red]"
            )
            logging.exception(e)
            return False
        except OpenAIError as e:
            self.console.print(
                f"[red]API Error. Type `r` or Ctrl-R to try again: {type(e)}: {e}[/red]"
            )
            logging.exception(e)
            return True

        next_response = {"role": "assistant", "content": next_response}
        logging.info(next_response)
        self.messages.append(next_response)
        return True

    def request_input(self):
        line = prompt(self.prompt_session)

        if line != "\\":
            return line

        return prompt(self.prompt_session, multiline=True)

    def _validate_args(self, args: Dict[str, Any]):
        for key in args:
            supported_overrides = self.assistant.supported_overrides()
            if key not in supported_overrides:
                self.console.print(
                    f"[red]Invalid argument: {key}. Allowed arguments: {supported_overrides}[/red]"
                )
                return False
        return True

    def parse_input(self, input: str) -> Tuple[str, ModelOverrides]:
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
        console = Console(width=80)
        console.print(Markdown(TERMINAL_WELCOME))

        while True:
            while (next_user_input := self.request_input()) == "":
                pass

            if next_user_input in COMMAND_QUIT:
                break
            elif next_user_input in COMMAND_CLEAR:
                self.clear()
                logging.info("Cleared the conversation.")
                continue
            elif next_user_input in COMMAND_RERUN:
                self.rerun()
                continue

            user_input, args = self.parse_input(next_user_input)
            if user_input is None:
                continue

            if args:
                self.console.print(
                    f"[bold yellow]Running model with: {args}[/bold yellow]"
                )

            user_message = {"role": "user", "content": user_input}
            logging.info(f"message: {user_message}, args: {args}")
            self.messages.append(user_message)
            self.user_prompts.append((user_message, args))
            if not self.respond(args):
                # Roll back the last user message
                self.messages = self.messages[:-1]
                self.user_prompts = self.user_prompts[:-1]
