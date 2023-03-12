import openai
import os
from blessings import Terminal
from prompt_toolkit import PromptSession

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer. Your responses are short and concise. You include code snippets when appropriate. Code snippets are formatted using Markdown. If the user asks a question about something other than software development, you are happy to help with that too."""

INIT_USER_PROMPT = """Your responses must be short and concise. Do not include explanations unless asked."""

TERMINAL_WELCOME = """
Hi! I'm here to help. Type `q` or Ctrl-D to exit, `r` or Ctrl-C to reset
the conversation. To enter multi-line mode, enter a backslash `\` followed
by a new line. Exit the multi-line mode by pressing ESC and then Enter.
"""

term = Terminal()


def complete_chat(messages):
    response_iter = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.5, stream=True
    )

    # Now iterate over the response iterator to yield the next response
    for response in response_iter:
        next_choice = response["choices"][0]
        if next_choice["finish_reason"] is None and "content" in next_choice["delta"]:
            yield next_choice["delta"]["content"]


def next_input(session):
    line = None
    try:
        line = session.prompt("> ", vi_mode=True, multiline=False)
    except EOFError:
        return "q"
    except KeyboardInterrupt:
        return "r"

    if line != "\\":
        return line

    try:
        return session.prompt("multiline> ", multiline=True, vi_mode=True)
    except (EOFError, KeyboardInterrupt):
        return next_input(session)


def init_messages():
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INIT_USER_PROMPT},
    ]


def respond(messages):
    next_response = []
    try:
        for response in complete_chat(messages):
            next_response.append(response)
            print(term.green(response), end="", flush=True)
    except KeyboardInterrupt:
        # If the user interrupts the chat completion, we'll just return what we have so far
        pass

    print("\n")
    next_response = {"role": "assistant", "content": "".join(next_response)}

    return next_response


def main():
    session = PromptSession()
    current_messages = init_messages()

    print(term.bold(TERMINAL_WELCOME))

    while True:
        while (next_user_input := next_input(session)) == "":
            pass

        if next_user_input in ("q", "quit"):
            break

        if next_user_input in ("r", "reset"):
            current_messages = init_messages()
            print(term.bold("Cleared the conversation."))
            continue

        current_messages.append({"role": "user", "content": next_user_input})

        next_response = respond(current_messages)
        current_messages.append(next_response)


if __name__ == "__main__":
    main()
