from typing import Iterator, List, cast
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

import tiktoken
import json

from gptcli.completion import CompletionProvider, Message


class OpenAICompletionProvider(CompletionProvider):
    def __init__(self):
        self.client = OpenAI(api_key=openai.api_key)

    def complete(
        self, messages: List[Message], args: dict, stream: bool = False, tools = []
    ) -> Iterator[str]:
        kwargs = {}
        if "temperature" in args:
            kwargs["temperature"] = args["temperature"]
        if "top_p" in args:
            kwargs["top_p"] = args["top_p"]
        if "type" in args:
            kwargs["type"] = args["type"]
        if "tool_choice" in args:
            kwargs["tool_choice"] = "required"

        #json loads until error or until tools is an object and not a string
        while (type(tools) == str):
            try:
                tools = json.loads(tools)
            except:
                break 
        

        if stream and len(tools) > 0:
            response_iter = self.client.chat.completions.create(
                messages=cast(List[ChatCompletionMessageParam], messages),
                stream=True,
                model=args["model"],
                tools=tools,
                **kwargs,
            )

            #for response in response_iter:
            #    next_choice = response.choices[0]
            #    if next_choice.finish_reason is None and next_choice.delta.content:
            #        yield next_choice.delta.content
            
            tool = False
            first = True
            for response in response_iter:
                delta = response.choices[0].delta
                if delta.tool_calls:
                    tool = True
                    for tool_call in delta.tool_calls:
                        if tool_call.function:
                            function_name = tool_call.function.name
                            function_arguments = tool_call.function.arguments
                            # Process the tool call
                            #print(f"Tool call: {function_name}")
                            #print(f"Arguments: {function_arguments}")
                            # You can invoke your tool function here
                            if (function_name):
                                #the observation with openai is they only start arguments after first
                                #providing the function_name 
                                #print function name no endline
                                #print (function_name, end="")
                                #print()
                                if (first):
                                    yield("[", True)
                                    first = False
                                else:
                                    yield("}, ", True)
                                yield ("{ \"tool_call\" : \""+function_name+"\", \"arguments\" : ", True)
                            elif (function_arguments):
                                #print (function_arguments, end="")
                                yield (function_arguments, True)
                    
                elif delta.content:
                    yield delta.content
            
            if (tool):
                yield (" }]", True)
            
                                    
        elif stream and len(tools) == 0:
            response_iter = self.client.chat.completions.create(
                messages=cast(List[ChatCompletionMessageParam], messages),
                stream=True,
                model=args["model"],
                **kwargs,
            )

            for response in response_iter:
                next_choice = response.choices[0]
                if next_choice.finish_reason is None and next_choice.delta.content:
                    yield next_choice.delta.content
        elif not stream and len(tools) > 0:
            response = self.client.chat.completions.create(
                messages=cast(List[ChatCompletionMessageParam], messages),
                model=args["model"],
                stream=False,
                tools=tools,
                **kwargs,
            )
            next_choice = response.choices[0]
            if next_choice.message.content:
                yield next_choice.message.content
        elif not stream and len(tools) == 0:
            response = self.client.chat.completions.create(
                messages=cast(List[ChatCompletionMessageParam], messages),
                model=args["model"],
                stream=False,
                **kwargs,
            )
            next_choice = response.choices[0]
            if next_choice.message.content:
                yield next_choice.message.content


def num_tokens_from_messages_openai(messages: List[Message], model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        for key, value in message.items():
            assert isinstance(value, str)
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def num_tokens_from_completion_openai(completion: Message, model: str) -> int:
    return num_tokens_from_messages_openai([completion], model)
