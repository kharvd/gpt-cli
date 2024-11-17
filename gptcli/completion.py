from abc import abstractmethod
from typing import Iterator, List, Literal, TypedDict, Union

from attr import dataclass


class Message(TypedDict):
    role: str
    content: str


class Pricing(TypedDict):
    prompt: float
    response: float


@dataclass
class MessageDeltaEvent:
    text: str
    type: Literal["message_delta"] = "message_delta"


@dataclass
class UsageEvent:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    type: Literal["usage"] = "usage"

    @staticmethod
    def with_pricing(
        prompt_tokens: int, completion_tokens: int, total_tokens: int, pricing: Pricing
    ) -> "UsageEvent":
        return UsageEvent(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=prompt_tokens * pricing["prompt"]
            + completion_tokens * pricing["response"],
        )


CompletionEvent = Union[MessageDeltaEvent, UsageEvent]


class CompletionProvider:
    @abstractmethod
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[CompletionEvent]:
        pass


class CompletionError(Exception):
    pass


class BadRequestError(CompletionError):
    pass
