import re
import logging
from prompt_toolkit import PromptSession
from openai import OpenAIError, InvalidRequestError
from rich.console import Console
from rich.markdown import Markdown
from typing import Any, Dict, List, Tuple

from gptcli.term_utils import (
    COMMAND_CLEAR,
    COMMAND_QUIT,
    COMMAND_RERUN,
    StreamingMarkdownPrinter,
    parse_args,
    prompt,
)
from gptcli.assistant import Assistant, ModelOverrides


TERMINAL_WELCOME = """
Hi! I'm here to help. Type `q` or Ctrl-D to exit, `c` or Ctrl-C to clear
the conversation, `r` or Ctrl-R to re-generate the last response. 
To enter multi-line mode, enter a backslash `\` followed by a new line.
Exit the multi-line mode by pressing ESC and then Enter (Meta+Enter).
"""


class ChatSession:
    def __init__(self, assistant: Assistant, markdown: bool):
        self.assistant = assistant
        self.messages = assistant.init_messages()
        self.user_prompts: List[Tuple[str, ModelOverrides]] = []
        self.prompt_session = PromptSession[str]()
        self.markdown = markdown
        self.console = Console()

    def _clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        self.console.print("[bold]Cleared the conversation.[/bold]")
        logging.info("Cleared the conversation.")

    def _rerun(self):
        if len(self.user_prompts) == 0:
            self.console.print("[bold]Nothing to re-run.[/bold]")
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        self.console.print("[bold]Re-running the last message.[/bold]")
        logging.info("Re-generating the last message.")
        _, args = self.user_prompts[-1]
        self._respond(args)

    def _respond(self, args: ModelOverrides) -> bool:
        """
        Respond to the user's input and return whether the assistant's response was saved.
        """
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

    def _request_input(self):
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

    def _parse_input(self, input: str) -> Tuple[str, ModelOverrides]:
        input, args = parse_args(input)
        if not self._validate_args(args):
            return None, {}

        return input, args

    def _add_user_message(self, user_input: str, args: ModelOverrides):
        user_message = {"role": "user", "content": user_input}
        logging.info(f"message: {user_message}, args: {args}")
        self.messages.append(user_message)
        self.user_prompts.append((user_message, args))

    def _rollback_user_message(self):
        self.messages = self.messages[:-1]
        self.user_prompts = self.user_prompts[:-1]

    def loop(self):
        console = Console(width=80)
        console.print(Markdown(TERMINAL_WELCOME))

        while True:
            while (next_user_input := self._request_input()) == "":
                pass

            if next_user_input in COMMAND_QUIT:
                break
            elif next_user_input in COMMAND_CLEAR:
                self._clear()
                continue
            elif next_user_input in COMMAND_RERUN:
                self._rerun()
                continue

            user_input, args = self._parse_input(next_user_input)
            if user_input is None:
                continue

            if args:
                self.console.print(
                    f"[bold yellow]Running model with: {args}[/bold yellow]"
                )

            self._add_user_message(user_input, args)
            response_saved = self._respond(args)
            if not response_saved:
                self._rollback_user_message()
