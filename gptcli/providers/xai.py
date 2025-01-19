import os
from typing import Optional

from openai import OpenAI

from gptcli.completion import Pricing
from gptcli.providers.openai import OpenAICompletionProvider

api_key = os.environ.get("XAI_API_KEY")


class XAICompletionProvider(OpenAICompletionProvider):
    def __init__(self):
        self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    def pricing(self, model: str) -> Optional[Pricing]:
        if model.startswith("grok-beta"):
            return GROK_BETA_PRICE_PER_TOKEN
        elif model.startswith("grok-2"):
            return GROK_2_PRICE_PER_TOKEN
        else:
            return None


GROK_2_PRICE_PER_TOKEN: Pricing = {
    "prompt": 2.00 / 1_000_000,
    "response": 10.00 / 1_000_000,
}

GROK_BETA_PRICE_PER_TOKEN: Pricing = {
    "prompt": 5.00 / 1_000_000,
    "response": 15.00 / 1_000_000,
}
