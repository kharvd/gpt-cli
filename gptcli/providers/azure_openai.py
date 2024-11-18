import openai
from openai import AzureOpenAI
from gptcli.providers.openai import OpenAICompletionProvider


class AzureOpenAICompletionProvider(OpenAICompletionProvider):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=openai.api_key,
            base_url=openai.base_url,
            api_version=openai.api_version,
        )
