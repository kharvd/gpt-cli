# gpt-cli

Command-line interface for ChatGPT optimized for software development.

![screenshot](./screenshot.png)

## Usage

Make sure to set the `OPENAI_API_KEY` environment variable to your OpenAI API key.

```bash
$ ./gpt.py
```

Type `q` or Ctrl-D to exit, `c` or Ctrl-C to clear the conversation, `r` or Ctrl-R to re-generate the last response.
To enter multi-line mode, enter a backslash `\` followed by a new line. Exit the multi-line mode by pressing ESC and then Enter.

By default, the assistant is instructed to be an expert in software development and provide short responses. You can use a more general assistant by running it with `general` argument:

```bash
$ ./gpt.py general
```
