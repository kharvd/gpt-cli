import logging
from abc import abstractmethod
from gptcli.assistant import Assistant, Message, ModelOverrides
from gptcli.term_utils import COMMAND_CLEAR, COMMAND_QUIT, COMMAND_RERUN
from openai import InvalidRequestError, OpenAIError
from typing import Any, Dict, List, Tuple


class ResponseStreamer:
    async def __aenter__(self):
        pass

    async def on_next_token(self, token: str):
        pass

    async def __aexit__(self, *args):
        pass


class ChatListener:
    async def on_chat_start(self):
        pass

    async def on_chat_clear(self):
        pass

    async def on_chat_rerun(self, success: bool):
        pass

    async def on_error(self, error: Exception):
        pass

    @abstractmethod
    def response_streamer(self) -> ResponseStreamer:
        pass

    async def on_chat_message(self, message: Message):
        pass


class UserInputProvider:
    async def get_user_input(self) -> Tuple[str, ModelOverrides]:
        pass


def InvalidArgumentError(Exception):
    def __init__(self, message: str):
        self.message = message


class ChatSession:
    def __init__(
        self,
        assistant: Assistant,
        listener: ChatListener,
    ):
        self.assistant = assistant
        self.messages = assistant.init_messages()
        self.user_prompts: List[Tuple[str, ModelOverrides]] = []
        self.listener = listener

    async def _clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        await self.listener.on_chat_clear()
        logging.info("Cleared the conversation.")

    async def _rerun(self):
        if len(self.user_prompts) == 0:
            await self.listener.on_chat_rerun(False)
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        logging.info("Re-generating the last message.")
        await self.listener.on_chat_rerun(True)
        _, args = self.user_prompts[-1]
        await self._respond(args)

    async def _respond(self, args: ModelOverrides) -> bool:
        """
        Respond to the user's input and return whether the assistant's response was saved.
        """
        next_response = ""
        try:
            completion_iter = self.assistant.complete_chat(
                self.messages, override_params=args
            )

            async with self.listener.response_streamer() as stream:
                async for response in completion_iter:
                    next_response += response
                    await stream.on_next_token(response)
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass
        except InvalidRequestError as e:
            logging.exception(e)
            await self.listener.on_error(e)
            return False
        except OpenAIError as e:
            logging.exception(e)
            await self.listener.on_error(e)
            return True

        logging.info("Assistant: %s", next_response)
        next_response = {"role": "assistant", "content": next_response}
        self.messages = self.messages + [next_response]
        await self.listener.on_chat_message(next_response)
        return True

    async def _validate_args(self, args: Dict[str, Any]):
        for key in args:
            supported_overrides = self.assistant.supported_overrides()
            if key not in supported_overrides:
                await self.listener.on_error(
                    InvalidArgumentError(
                        f"Invalid argument: {key}. Allowed arguments: {supported_overrides}"
                    )
                )
                return False
        return True

    async def _add_user_message(self, user_input: str, args: ModelOverrides):
        logging.info("User: %s", user_input)
        user_message = {"role": "user", "content": user_input}
        self.messages = self.messages + [user_message]
        await self.listener.on_chat_message(user_message)
        self.user_prompts.append((user_message, args))

    def _rollback_user_message(self):
        self.messages = self.messages[:-1]
        self.user_prompts = self.user_prompts[:-1]

    async def process_input(self, user_input: str, args: ModelOverrides):
        """
        Process the user's input and return whether the session should continue.
        """
        if not await self._validate_args(args):
            return True

        if user_input in COMMAND_QUIT:
            return False
        elif user_input in COMMAND_CLEAR:
            await self._clear()
            return True
        elif user_input in COMMAND_RERUN:
            await self._rerun()
            return True

        await self._add_user_message(user_input, args)
        response_saved = await self._respond(args)
        if not response_saved:
            self._rollback_user_message()

        return True

    async def loop(self, input_provider: UserInputProvider):
        await self.listener.on_chat_start()
        while await self.process_input(*await input_provider.get_user_input()):
            pass
        return
