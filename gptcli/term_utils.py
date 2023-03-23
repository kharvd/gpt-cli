import re
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from rich.live import Live
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from typing import Any, Dict, Optional, Tuple


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


def parse_args(input: str) -> Tuple[str, Dict[str, Any]]:
    args = {}
    regex = r"--(\w+)(?:\s+|=)([^\s]+)"
    matches = re.findall(regex, input)
    if matches:
        args = dict(matches)
        input = input.split("--")[0].strip()

    return input, args
