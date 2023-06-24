from abc import abstractmethod
import logging
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


def merge_dicts(a, b):
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


def make_completion(
    content_delta: str,
    role: str = "assistant",
    finish_reason: Optional[str] = None,
) -> Completion:
    delta: Message = {
        "role": role,
        "content": content_delta,
    }
    return {
        "delta": delta,
        "finish_reason": finish_reason,
    }


def make_completion_iter(
    content_iter: Iterator[str],
    role: str = "assistant",
    finish_reason: Optional[str] = "stop",
) -> Iterator[Completion]:
    logging.debug("make_completion_iter")
    yield make_completion("", role=role)
    for content in content_iter:
        yield make_completion(content, role="")
    yield make_completion("", role="", finish_reason=finish_reason)


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
