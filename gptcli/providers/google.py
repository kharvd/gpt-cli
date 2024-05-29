import google.generativeai as genai
from google.generativeai.types.content_types import ContentDict
from google.generativeai.types.generation_types import GenerationConfig
from google.generativeai.types.safety_types import (
    HarmBlockThreshold,
    HarmCategory,
)
from typing import Iterator, List, Optional

from gptcli.completion import (
    CompletionEvent,
    CompletionProvider,
    Message,
    MessageDeltaEvent,
    Pricing,
    UsageEvent,
)

ROLE_MAP = {
    "user": "user",
    "assistant": "model",
}


def map_message(message: Message) -> ContentDict:
    return {"role": ROLE_MAP[message["role"]], "parts": [message["content"]]}


SAFETY_SETTINGS = [
    {"category": category, "threshold": HarmBlockThreshold.BLOCK_NONE}
    for category in [
        HarmCategory.HARM_CATEGORY_HARASSMENT,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    ]
]


class GoogleCompletionProvider(CompletionProvider):
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        generation_config = GenerationConfig(
            temperature=args.get("temperature"),
            top_p=args.get("top_p"),
        )

        model_name = args["model"]

        if messages[0]["role"] == "system":
            system_instruction = messages[0]["content"]
            messages = messages[1:]
        else:
            system_instruction = None

        chat_history = [map_message(m) for m in messages]

        model = genai.GenerativeModel(model_name, system_instruction=system_instruction)

        if stream:
            response = model.generate_content(
                chat_history,
                generation_config=generation_config,
                safety_settings=SAFETY_SETTINGS,
                stream=True,
            )

            for chunk in response:
                yield MessageDeltaEvent(chunk.text)

        else:
            response = model.generate_content(
                chat_history,
                generation_config=generation_config,
                safety_settings=SAFETY_SETTINGS,
            )
            yield MessageDeltaEvent(response.text)

        prompt_tokens = response.usage_metadata.prompt_token_count
        completion_tokens = response.usage_metadata.candidates_token_count
        total_tokens = prompt_tokens + completion_tokens
        pricing = get_gemini_pricing(model_name, prompt_tokens)
        if pricing:
            yield UsageEvent.with_pricing(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                pricing=pricing,
            )


def get_gemini_pricing(model: str, prompt_tokens: int) -> Optional[Pricing]:
    if model.startswith("gemini-1.5-flash"):
        return {
            "prompt": (0.35 if prompt_tokens < 128000 else 0.7) / 1_000_000,
            "response": (1.05 if prompt_tokens < 128000 else 2.10) / 1_000_000,
        }
    elif model.startswith("gemini-1.5-pro"):
        return {
            "prompt": (3.50 if prompt_tokens < 128000 else 7.00) / 1_000_000,
            "response": (10.5 if prompt_tokens < 128000 else 21.0) / 1_000_000,
        }
    elif model.startswith("gemini-pro"):
        return {
            "prompt": 0.50 / 1_000_000,
            "response": 1.50 / 1_000_000,
        }
    else:
        return None
