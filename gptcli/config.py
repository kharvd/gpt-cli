import os
from typing import Dict, Optional
from attr import dataclass
import yaml

from gptcli.assistant import AssistantConfig

CONFIG_FILE_PATH = os.path.join(
    os.path.expanduser("~"), ".config", "gpt-cli", "gpt.yml"
)


@dataclass
class GptCliConfig:
    default_assistant: str = "general"
    markdown: bool = True
    show_price: bool = True
    api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    log_file: Optional[str] = None
    log_level: str = "INFO"
    assistants: Dict[str, AssistantConfig] = {}
    interactive: Optional[bool] = None


def read_yaml_config(file_path: str) -> GptCliConfig:
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
        return GptCliConfig(
            **config,
        )
