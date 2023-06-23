from abc import abstractmethod
from typing import Iterator, List, Optional, TypedDict
from typing_extensions import Required


class FunctionCall(TypedDict, total=False):
    name: str
    arguments: str


class Message(TypedDict, total=False):
    role: Required[str]
    content: Optional[str]
    name: str
    function_call: FunctionCall


def merge_dicts(a: dict, b: dict):
    """
    Given two nested dicts with string values, merge dict `b` into dict `a`, concatenating
    string values.
    """
    for key, value in b.items():
        if isinstance(value, dict):
            a[key] = merge_dicts(a.get(key, {}), value)
        elif value is not None:
            a[key] = a.get(key, "") + value
    return a


class ModelOverrides(TypedDict, total=False):
    model: str
    temperature: float
    top_p: float
    enable_code_execution: bool


class CompletionDelta(TypedDict):
    content: Optional[str]
    function_call: Optional[FunctionCall]


class Completion(TypedDict):
    delta: Message
    finish_reason: Optional[str]


class CompletionProvider:
    @abstractmethod
    def complete(
        self,
        messages: List[Message],
        args: dict,
        stream: bool = False,
        enable_code_execution: bool = False,
    ) -> Iterator[Completion]:
        pass
