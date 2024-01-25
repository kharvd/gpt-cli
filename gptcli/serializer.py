import json
import os
from typing import List
from gptcli.completion import Message
from datetime import datetime
import pytz


class Conversation:
    def __init__(self, topic: str, messages: List[Message], id: int = None):
        self.topic = topic
        # 如果没有提供id，生成北京时间的时间戳
        if id is None:
            beijing_tz = pytz.timezone(
                'Asia/Shanghai')  # 获取北京时区
            now = datetime.now(
                beijing_tz)  # 获取当前北京时间
            self.id = now.strftime(
                '%Y%m%d%H%M%S')  # 格式化时间戳
        else:
            self.id = id
        self.messages: List[Message] = messages


class ConversationSerializer:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation

    def dump(self, directory: str) -> str:
        """序列化会话并保存到磁盘，文件名为ID"""
        file_name = f"{self.conversation.id}.json"
        file_path = os.path.join(directory, file_name)
        data = {
            'topic': self.conversation.topic,
            'messages': self.conversation.messages
        }
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        return file_path  # 返回文件路径，以便知道文件保存位置

    def load(self, file_path: str) -> None:
        """从磁盘加载会话并反序列化"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # 提取文件名中的时间戳作为id
            file_name = os.path.basename(file_path)
            conversation_id = int(os.path.splitext(file_name)[0])
            self.conversation = Conversation(topic=data['topic'], messages=data['messages'], id=conversation_id)
