import glob
import os

from gptcli.config import GptCliConfig
from gptcli.renderer import Renderer
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
    config = GptCliConfig()
    save_directory = config.conversations_save_directory

    # 使用glob模块的glob函数，获取指定文件夹下的所有.json文件
    for filename in glob.glob(os.path.join(save_directory, '*.json')):
        # 使用os模块的splitext函数，分离文件名和扩展名
        serializer = ConversationSerializer(None)
        serializer.load(filename)
        base_name = os.path.basename(filename)
        file_name_without_extension = os.path.splitext(base_name)[0]
        renderer = Renderer()
        content = renderer.render("conversation.md", serializer.conversation)
        file_name = f"{file_name_without_extension}.md"
        file_path = os.path.join(save_directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
