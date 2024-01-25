import glob
from abc import abstractmethod
import os
import pytz
from datetime import datetime
from typing_extensions import TypeGuard
from gptcli.assistant import Assistant
from gptcli.completion import Message, ModelOverrides
from openai import BadRequestError, OpenAIError
from typing import Any, Dict, List, Tuple

from gptcli.config import GptCliConfig
from gptcli.renderer import render
from gptcli.serializer import Conversation, ConversationSerializer


def render_jsons():
    config = GptCliConfig()

    # 使用glob模块的glob函数，获取指定文件夹下的所有.json文件
    for filename in glob.glob(os.path.join(config.conversations_save_directory, '*.json')):
        # 使用os模块的splitext函数，分离文件名和扩展名
        serializer = ConversationSerializer(None)
        serializer.load(filename)
        base_name = os.path.basename(filename)
        file_name_without_extension = os.path.splitext(base_name)[0]
        content = render("""
# {{data.topic}}                                                                                                                                                                                             
                                                                                                                                                                                                                
{% for message in data.messages %}                                                                                                                                                                             
**{{message.role}}**: 

{{message.content}}                                                                                                                                                                      
{% endfor %}      
        """, serializer.conversation)
        file_name = f"{file_name_without_extension}.md"
        file_path = os.path.join(config.conversations_render_directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)


class ResponseStreamer:
    def __enter__(self) -> "ResponseStreamer":
        return self

    def on_next_token(self, token: str):
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


COMMAND_CLEAR = (":clear", ":c")
COMMAND_QUIT = (":quit", ":q")
COMMAND_RERUN = (":rerun", ":r")
COMMAND_HELP = (":help", ":h", ":?")
COMMAND_SAVE = (":save", ":s")
ALL_COMMANDS = [*COMMAND_CLEAR, *COMMAND_QUIT, *COMMAND_RERUN, *COMMAND_HELP, *COMMAND_SAVE]
COMMANDS_HELP = """
Commands:
- `:clear` / `:c` / Ctrl+C - Clear the conversation.
- `:quit` / `:q` / Ctrl+D - Quit the program.
- `:rerun` / `:r` / Ctrl+R - Re-run the last message.
- `:help` / `:h` / `:?` - Show this help message.
- `:save` / `:s` / Ctrl+S - Save the conversation.
"""


def generate_session_id():
    beijing_tz = pytz.timezone(
        'Asia/Shanghai')  # 获取北京时区
    now = datetime.now(
        beijing_tz)  # 获取当前北京时间
    return now.strftime('%Y%m%d%H%M%S')  # 格式化时间戳


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
        self.session_id = generate_session_id()  # 新增会话ID

    def _clear(self):
        self.messages = self.assistant.init_messages()
        self.user_prompts = []
        self.listener.on_chat_clear()
        self.session_id = generate_session_id()

    def _save(self):
        if len(self.messages) > 0:
            topic = self.messages[0]["content"]
            conversation = Conversation(topic=topic, messages=self.messages, id=int(self.session_id))
            serializer = ConversationSerializer(conversation)
            config = GptCliConfig()
            save_directory = config.conversations_save_directory
            os.makedirs(save_directory, exist_ok=True)
            serializer.dump(save_directory)
            render_jsons()

    def _rerun(self):
        if len(self.user_prompts) == 0:
            self.listener.on_chat_rerun(False)
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages = self.messages[:-1]

        self.listener.on_chat_rerun(True)
        _, args = self.user_prompts[-1]
        self._respond(args)

    def _respond(self, args: ModelOverrides) -> bool:
        """
        Respond to the user's input and return whether the assistant's response was saved.
        """
        next_response: str = ""
        try:
            completion_iter = self.assistant.complete_chat(
                self.messages, override_params=args
            )

            with self.listener.response_streamer() as stream:
                for response in completion_iter:
                    next_response += response
                    stream.on_next_token(response)
        except KeyboardInterrupt:
            # If the user interrupts the chat completion, we'll just return what we have so far
            pass
        except BadRequestError as e:
            self.listener.on_error(e)
            return False
        except OpenAIError as e:
            self.listener.on_error(e)
            return True

        next_message: Message = {"role": "assistant", "content": next_response}
        self.listener.on_chat_message(next_message)
        self.listener.on_chat_response(self.messages, next_message, args)

        self.messages = self.messages + [next_message]
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

    def _print_help(self):
        with self.listener.response_streamer() as stream:
            stream.on_next_token(COMMANDS_HELP)

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
        elif user_input in COMMAND_SAVE:
            self._save()
            return True
        elif user_input in COMMAND_HELP:
            self._print_help()
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
