from abc import abstractmethod
import logging
import json
import traceback
import base64
from typing_extensions import TypeGuard
from gptcli.assistant import Assistant
from gptcli.completion import FunctionCall, Message, ModelOverrides, merge_dicts
from openai import InvalidRequestError, OpenAIError
from typing import Any, Dict, List, Optional, Tuple


class ResponseStreamer:
    def __enter__(self) -> "ResponseStreamer":
        return self

    def on_message_delta(self, message_delta: Message):
        pass

    def on_function_result(self, result: dict):
        pass

    def __exit__(self, *args):
        pass


class ChatListener:
    def on_chat_start(self):
        pass

    def on_chat_clear(self):
        pass

    def on_chat_rerun(self, success: bool):
        pass

    def on_error(self, error: Exception):
        pass

    def response_streamer(self) -> ResponseStreamer:
        return ResponseStreamer()

    def on_chat_message(self, message: Message):
        pass

    def on_function_call(self, function_name: str, **kwargs) -> Optional[dict]:
        pass

    def on_chat_response(
        self, messages: List[Message], response: Message, overrides: ModelOverrides
    ):
        pass


class UserInputProvider:
    @abstractmethod
    def get_user_input(self) -> Tuple[str, Dict[str, Any]]:
        pass


class InvalidArgumentError(Exception):
    def __init__(self, message: str):
        self.message = message


COMMAND_CLEAR = ("clear", "c")
COMMAND_QUIT = ("quit", "q")
COMMAND_RERUN = ("rerun", "r")
ALL_COMMANDS = [*COMMAND_CLEAR, *COMMAND_QUIT, *COMMAND_RERUN]


class ChatSession:
    def __init__(
        self,
        assistant: Assistant,
        listener: ChatListener,
    ):
        self.assistant = assistant
        self.messages: List[Message] = assistant.init_messages()
        self.user_prompts: List[Tuple[Message, ModelOverrides]] = []
        self.listener = listener

    def _clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        self.listener.on_chat_clear()

    def _rerun(self):
        if len(self.user_prompts) == 0:
            self.listener.on_chat_rerun(False)
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        self.listener.on_chat_rerun(True)
        _, args = self.user_prompts[-1]
        self._respond(args)

    def _completion(self, args: ModelOverrides):
        next_message = {
            "role": "",
        }
        finish_reason = None

        completion_iter = self.assistant.complete_chat(
            self.messages, override_params=args
        )

        try:
            with self.listener.response_streamer() as stream:
                for completion in completion_iter:
                    next_message = merge_dicts(next_message, completion["delta"])
                    stream.on_message_delta(completion["delta"])
                    finish_reason = completion["finish_reason"]

                if next_message.get("function_call") is not None:
                    logging.debug(f"Function call: {next_message['function_call']}")
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass

        if "content" not in next_message:
            next_message["content"] = None

        return {
            "message": next_message,
            "finish_reason": finish_reason,
        }

    def _handle_function_call(self, function_call: FunctionCall) -> Message:
        function_name = function_call.get("name", "null")

        function_result = None
        try:
            function_arguments = json.loads(function_call["arguments"])
            function_result = self.listener.on_function_call(
                function_name, **function_arguments
            )
        except Exception:
            function_result = {
                "text/plain": f"Exception occurred:\n\n```{traceback.format_exc()}```"
            }

        content = ""
        if function_result:
            with self.listener.response_streamer() as stream:
                stream.on_function_result(function_result)
            content = function_result.get("text/plain")

        return {
            "role": "function",
            "name": function_name,
            "content": content,
        }

    def _respond(self, args: ModelOverrides) -> bool:
        """
        Respond to the user's input and return whether the assistant's response was saved.
        """
        finish_reason: Optional[str] = None

        while finish_reason != "stop":
            try:
                completion = self._completion(args)
                next_message = completion["message"]
                finish_reason = completion["finish_reason"]

                if finish_reason is None:
                    # If the user interrupts the chat completion, we'll stop here
                    break

            except InvalidRequestError as e:
                self.listener.on_error(e)
                return False
            except OpenAIError as e:
                self.listener.on_error(e)
                return True

            self.messages = self.messages + [next_message]
            self.listener.on_chat_message(next_message)
            self.listener.on_chat_response(self.messages, next_message, args)
            if finish_reason == "function_call":
                function_message = self._handle_function_call(
                    next_message["function_call"]
                )
                self.messages = self.messages + [function_message]
                self.listener.on_chat_message(function_message)

        return True

    def _validate_args(self, args: Dict[str, Any]) -> TypeGuard[ModelOverrides]:
        for key in args:
            supported_overrides = self.assistant.supported_overrides()
            if key not in supported_overrides:
                self.listener.on_error(
                    InvalidArgumentError(
                        f"Invalid argument: {key}. Allowed arguments: {supported_overrides}"
                    )
                )
                return False
        return True

    def _add_user_message(self, user_input: str, args: ModelOverrides):
        user_message: Message = {"role": "user", "content": user_input}
        self.messages = self.messages + [user_message]
        self.listener.on_chat_message(user_message)
        self.user_prompts.append((user_message, args))

    def _rollback_user_message(self):
        self.messages = self.messages[:-1]
        self.user_prompts = self.user_prompts[:-1]

    def process_input(self, user_input: str, args: Dict[str, Any]):
        """
        Process the user's input and return whether the session should continue.
        """
        if not self._validate_args(args):
            return True

        if user_input in COMMAND_QUIT:
            return False
        elif user_input in COMMAND_CLEAR:
            self._clear()
            return True
        elif user_input in COMMAND_RERUN:
            self._rerun()
            return True

        self._add_user_message(user_input, args)
        response_saved = self._respond(args)
        if not response_saved:
            self._rollback_user_message()

        return True

    def loop(self, input_provider: UserInputProvider):
        self.listener.on_chat_start()
        while self.process_input(*input_provider.get_user_input()):
            pass
