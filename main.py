import openai
import os
import sys
import colorama

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
You are a helpful assistant who is an expert in software development. You are helping a user who is a software developer.
Your responses are concise and to the point. You can use natural language to ask questions and give answers.
You include code snippets when appropriate. Code snippets are formatted using Markdown.
"""


def complete_chat(messages):
    response_iter = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.5, stream=True
    )

    # Now iterate over the response iterator to yield the next response
    for response in response_iter:
        next_choice = response["choices"][0]
        if next_choice["finish_reason"] is None and "content" in next_choice["delta"]:
            yield next_choice["delta"]["content"]


def next_input():
    print("> ", end="", flush=True)
    line = sys.stdin.readline()
    if line == "":
        return "q"

    line = line.strip()

    if line != "'":
        return line

    lines = []
    while True:
        line = sys.stdin.readline()
        if line == "'\n":
            break
        lines.append(line)
    result = "".join(lines)

    return result


def init_messages():
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]


def respond(messages):
    next_response = []
    print(colorama.Fore.GREEN, end="")
    for response in complete_chat(messages):
        next_response.append(response)
        print(response, end="")
    print("\n")
    print(colorama.Fore.RESET, end="")

    next_response = {"role": "assistant", "content": "".join(next_response)}
    return next_response


def main():
    current_messages = init_messages()

    print(colorama.Style.BRIGHT, end="")
    print("Welcome to the chatbot. Ask a question about software development.")
    print(
        "Type 'q' to exit, 'r' to reset. Input a single quote to enter multi-line mode."
    )
    print("Exit multi-line mode by entering a single quote on a line by itself.")
    print(colorama.Style.RESET_ALL)

    while True:
        while (next_user_input := next_input()) == "":
            pass

        if next_user_input == "q":
            break

        if next_user_input == "r":
            current_messages = init_messages()
            print(colorama.Style.BRIGHT + "Resetting" + colorama.Style.RESET_ALL)
            continue

        current_messages.append({"role": "user", "content": next_user_input})

        next_response = respond(current_messages)
        current_messages.append(next_response)


if __name__ == "__main__":
    main()
