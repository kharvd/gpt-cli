import base64
import logging
import re
import json
from imgcat import imgcat
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from openai import OpenAIError, InvalidRequestError
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from typing import Any, Dict, Optional, Tuple

from rich.text import Text
from gptcli.completion import FunctionCall, Message, merge_dicts
from gptcli.session import (
    ALL_COMMANDS,
    COMMAND_CLEAR,
    COMMAND_QUIT,
    COMMAND_RERUN,
    ChatListener,
    InvalidArgumentError,
    ResponseStreamer,
    UserInputProvider,
)


TERMINAL_WELCOME = """
Hi! I'm here to help. Type `q` or Ctrl-D to exit, `c` or Ctrl-C to clear
the conversation, `r` or Ctrl-R to re-generate the last response.
To enter multi-line mode, enter a backslash `\\` followed by a new line.
Exit the multi-line mode by pressing ESC and then Enter (Meta+Enter).
"""


class StreamingMarkdownPrinter:
    def __init__(self, console: Console, markdown: bool):
        self.console = console
        self.current_message = {}
        self.markdown = markdown
        self.live: Optional[Live] = None

    def __enter__(self) -> "StreamingMarkdownPrinter":
        if self.markdown:
            self.live = Live(
                console=self.console, auto_refresh=False, vertical_overflow="visible"
            )
            self.live.__enter__()
        return self

    def _format_function_call(self, function_call: FunctionCall) -> str:
        text = ""
        if function_call.get("name") == "python_eval":
            source = function_call.get("arguments", "")
            try:
                source = json.loads(source).get("source", "")
            except:
                source = source + '"}'
                try:
                    source = json.loads(source).get("source", "")
                except:
                    source = ""

            text += "\n\nExecuting Python code:\n"
            text += f"```python\n{source}\n```"
        else:
            function_name = function_call.get("name", "?")
            function_arguments = function_call.get("arguments", {})
            text += f"""\n
Calling function:

```
{function_name}({function_arguments})
```"""
        return text

    def print(self, message_delta: Message):
        self.current_message = merge_dicts(self.current_message, message_delta)

        if self.markdown:
            assert self.live
            text = self.current_message.get("content", "")

            function_call = self.current_message.get("function_call")
            if function_call:
                text += self._format_function_call(function_call)

            content = Markdown(text, style="green")
            self.live.update(content)
            self.live.refresh()
        else:
            self.console.print(
                Text(message_delta.get("content") or "", style="green"), end=""
            )

    def __exit__(self, *args):
        if self.markdown:
            assert self.live
            self.live.__exit__(*args)
        self.console.print()


class CLIResponseStreamer(ResponseStreamer):
    def __init__(self, console: Console, markdown: bool):
        self.console = console
        self.markdown = markdown
        self.printer = StreamingMarkdownPrinter(self.console, self.markdown)

    def __enter__(self):
        self.printer.__enter__()
        return self

    def on_message_delta(self, message_delta: Message):
        self.printer.print(message_delta)

    def on_function_result(self, result: dict):
        self.console.print(Text("Function result:", style="yellow"))
        if "image/png" in result:
            image_base64 = result["image/png"]
            image_bytes = base64.b64decode(image_base64)
            imgcat(image_bytes)
        if "text/plain" in result:
            text = result["text/plain"]
            if self.markdown:
                content = Markdown(
                    f"```\n{text}\n```",
                )
            else:
                content = Text(text, style="yellow")
            self.console.print(content)

    def __exit__(self, *args):
        self.printer.__exit__(*args)


class CLIChatListener(ChatListener):
    def __init__(self, markdown: bool):
        self.markdown = markdown
        self.console = Console()

    def on_chat_start(self):
        console = Console(width=80)
        console.print(Markdown(TERMINAL_WELCOME))

    def on_chat_clear(self):
        self.console.print("[bold]Cleared the conversation.[/bold]")

    def on_chat_rerun(self, success: bool):
        if success:
            self.console.print("[bold]Re-running the last message.[/bold]")
        else:
            self.console.print("[bold]Nothing to re-run.[/bold]")

    def on_error(self, e: Exception):
        if isinstance(e, InvalidRequestError):
            self.console.print(
                f"[red]Request Error. The last prompt was not saved: {type(e)}: {e}[/red]"
            )
        elif isinstance(e, OpenAIError):
            self.console.print(
                f"[red]API Error. Type `r` or Ctrl-R to try again: {type(e)}: {e}[/red]"
            )
        elif isinstance(e, InvalidArgumentError):
            self.console.print(f"[red]{e.message}[/red]")
        else:
            self.console.print(f"[red]Error: {type(e)}: {e}[/red]")

    def response_streamer(self) -> ResponseStreamer:
        return CLIResponseStreamer(self.console, self.markdown)


def parse_args(input: str) -> Tuple[str, Dict[str, Any]]:
    args = {}
    regex = r"--(\w+)(?:\s+|=)([^\s]+)"
    matches = re.findall(regex, input)
    if matches:
        args = dict(matches)
        input = input.split("--")[0].strip()

    return input, args


class CLIFileHistory(FileHistory):
    def append_string(self, string: str) -> None:
        if string in ALL_COMMANDS:
            return
        return super().append_string(string)


class CLIUserInputProvider(UserInputProvider):
    def __init__(self, history_filename) -> None:
        self.prompt_session = PromptSession[str](
            history=CLIFileHistory(history_filename)
        )

    def get_user_input(self) -> Tuple[str, Dict[str, Any]]:
        while (next_user_input := self._request_input()) == "":
            pass

        user_input, args = self._parse_input(next_user_input)
        return user_input, args

    def prompt(self, multiline=False):
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
            return self.prompt_session.prompt(
                "> " if not multiline else "multiline> ",
                vi_mode=True,
                multiline=multiline,
                enable_open_in_editor=True,
                key_bindings=bindings,
            )
        except KeyboardInterrupt:
            return ""

    def _request_input(self):
        line = self.prompt()

        if line != "\\":
            return line

        return self.prompt(multiline=True)

    def _parse_input(self, input: str) -> Tuple[str, Dict[str, Any]]:
        input, args = parse_args(input)
        return input, args
