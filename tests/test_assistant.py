import pytest
from gptcli.assistant import AssistantGlobalArgs, init_assistant


@pytest.mark.parametrize(
    "args,custom_assistants,expected_config",
    [
        (
            AssistantGlobalArgs("dev"),
            {},
            {},
        ),
        (
            AssistantGlobalArgs("dev", model="gpt-4"),
            {},
            {"model": "gpt-4"},
        ),
        (
            AssistantGlobalArgs("dev", temperature=0.5, top_p=0.5),
            {},
            {"temperature": 0.5, "top_p": 0.5},
        ),
        (
            AssistantGlobalArgs("dev"),
            {
                "dev": {
                    "model": "gpt-4",
                },
            },
            {"model": "gpt-4"},
        ),
        (
            AssistantGlobalArgs("dev", model="gpt-4"),
            {
                "dev": {
                    "model": "gpt-3.5-turbo",
                },
            },
            {"model": "gpt-4"},
        ),
        (
            AssistantGlobalArgs("custom"),
            {
                "custom": {
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "top_p": 0.5,
                    "messages": [],
                },
            },
            {"model": "gpt-4", "temperature": 0.5, "top_p": 0.5},
        ),
        (
            AssistantGlobalArgs(
                "custom", model="gpt-3.5-turbo", temperature=1.0, top_p=1.0
            ),
            {
                "custom": {
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "top_p": 0.5,
                    "messages": [],
                },
            },
            {"model": "gpt-3.5-turbo", "temperature": 1.0, "top_p": 1.0},
        ),
    ],
)
def test_init_assistant(args, custom_assistants, expected_config):
    assistant = init_assistant(args, custom_assistants)
    assert assistant.config.get("model") == expected_config.get("model")
    assert assistant.config.get("temperature") == expected_config.get("temperature")
    assert assistant.config.get("top_p") == expected_config.get("top_p")
