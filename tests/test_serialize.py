import glob
import os

from gptcli.session import render_jsons
from gptcli.config import GptCliConfig
from gptcli.serializer import Conversation, ConversationSerializer


def test_serialize():
    # 使用示例
    messages = [
        {"role": "admin", "content": "Hello, world!"},
        {"role": "user", "content": "Hi there!"}
    ]

    # 创建一个 Conversation 对象，id将自动生成为当前时间戳
    conversation = Conversation(topic="General Discussion", messages=messages)
    serializer = ConversationSerializer(conversation)

    # 确保保存序列化数据的目录存在
    config = GptCliConfig()
    save_directory = config.conversations_save_directory
    os.makedirs(save_directory, exist_ok=True)

    # 序列化到磁盘
    file_path = serializer.dump(save_directory)
    print(f"Conversation saved to {file_path}")

    # 从磁盘加载数据
    serializer.load(file_path)
    print(serializer.conversation.topic, serializer.conversation.id, serializer.conversation.messages)


def test_render():
    render_jsons()
