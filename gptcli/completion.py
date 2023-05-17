from abc import abstractmethod
from typing import Iterator, List, TypedDict


class Message(TypedDict):
    role: str
    content: str


class ModelOverrides(TypedDict, total=False):
    model: str
    temperature: float
    top_p: float


class CompletionProvider:
    @abstractmethod
    def complete(
        self, messages: List[Message], args: dict, stream: bool = False
    ) -> Iterator[str]:
        pass
