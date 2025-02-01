import os
from typing import Dict, List, Optional

import yaml
from attr import dataclass

from gptcli.providers.llama import LLaMAModelConfig
from gptcli.completion import Message

CONFIG_FILE_PATHS = [
    os.path.join(os.path.expanduser("~"), ".config", "gpt-cli", "gpt.yml"),
    os.path.join(os.path.expanduser("~"), ".gptrc"),
]

class AssistantConfig:
    messages: List[Message]
    model: str
    openai_base_url_override: Optional[str]
    openai_api_key_override: Optional[str]
    temperature: float
    top_p: float

@dataclass
class ModelConfig:
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    pricing: Optional[Dict[str, float]] = None

@dataclass
class GptCliConfig:
    default_assistant: str = "general"
    markdown: bool = True
    show_price: bool = True
    api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    openai_api_key: Optional[str] = os.environ.get("OPENAI_API_KEY")
    openai_base_url: Optional[str] = os.environ.get("OPENAI_BASE_URL")
    openai_azure_api_version: str = "2024-10-21"
    anthropic_api_key: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = os.environ.get("GOOGLE_API_KEY")
    cohere_api_key: Optional[str] = os.environ.get("COHERE_API_KEY")
    log_file: Optional[str] = None
    log_level: str = "INFO"
    assistants: Dict[str, AssistantConfig] = {}
    interactive: Optional[bool] = None
    llama_models: Optional[Dict[str, LLaMAModelConfig]] = None
    model_configs: Optional[Dict[str, ModelConfig]] = None

def choose_config_file(paths: List[str]) -> str:
    for path in paths:
        if os.path.isfile(path):
            return path
    return ""


# Custom YAML Loader with !include support
class CustomLoader(yaml.SafeLoader):
    pass


def include_constructor(loader, node):
    # Get the file path from the node
    file_path = loader.construct_scalar(node)
    # Read and return the content of the included file
    with open(file_path, "r") as include_file:
        return include_file.read()


# Register the !include constructor
CustomLoader.add_constructor("!include", include_constructor)


def read_yaml_config(file_path: str) -> GptCliConfig:
    with open(file_path, "r") as file:
        config = yaml.load(file, Loader=CustomLoader)
        return GptCliConfig(**config)
