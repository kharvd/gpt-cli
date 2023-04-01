import os
import logging
import sys
import subprocess
import tempfile
from gptcli.assistant import Assistant


async def simple_response(assistant: Assistant, prompt: str, stream: bool) -> None:
    messages = assistant.init_messages()
    messages.append({"role": "user", "content": prompt})
    logging.info("User: %s", prompt)
    response_iter = assistant.complete_chat(messages, stream=stream)
    result = ""
    try:
        async for response in response_iter:
            result += response
            sys.stdout.write(response)
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.flush()
        logging.info("Assistant: %s", result)


async def execute(assistant: Assistant, prompt: str) -> None:
    messages = assistant.init_messages()
    messages.append({"role": "user", "content": prompt})
    logging.info("User: %s", prompt)
    response_iter = assistant.complete_chat(messages, stream=False)
    result = await response_iter.__anext__()
    logging.info("Assistant: %s", result)

    with tempfile.NamedTemporaryFile(mode="w", prefix="gptcli-", delete=False) as f:
        f.write("# Edit the command to execute below. Save and exit to execute it.\n")
        f.write("# Delete the contents to cancel.\n")
        f.write(result)
        f.flush()

    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, f.name])

    with open(f.name) as f:
        lines = [line for line in f.readlines() if not line.startswith("#")]
        command = "".join(lines).strip()

    if command == "":
        print("No command to execute.")
        return

    shell = os.environ.get("SHELL", "/bin/bash")

    logging.info(f"Executing: {command}")
    print(f"Executing:\n{command}")
    subprocess.run([shell, f.name])
