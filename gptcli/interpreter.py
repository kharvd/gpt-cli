import logging
from typing import Optional
from jupyter_client.manager import KernelManager
from queue import Empty

from gptcli.session import ChatListener


class CodeInterpreterSession:
    def __init__(self):
        self.logger = logging.getLogger("gptcli-code-interpreter")

        self.km = KernelManager()
        self.km.start_kernel()

        self.client = self.km.client()
        self.client.start_channels()

        # allow installing packages
        self.execute("%colors NoColor")
        self.execute("%load_ext autoreload")
        self.execute("%autoreload 2")
        self.execute("%matplotlib inline")
        self.execute(
            """
import matplotlib.pyplot as plt
plt.ioff()
"""
        )

    def execute(self, code: str) -> dict:
        self.logger.debug("Executing code: '%s'", code)

        msg_id = self.client.execute(code)
        state = "busy"
        output = {}
        while state != "idle":
            try:
                msg = self.client.get_iopub_msg(timeout=1)
                content = msg["content"]
                msg_type = msg["msg_type"]

                if msg_type == "execute_result" or msg_type == "display_data":
                    output = content["data"]
                elif msg_type == "stream":
                    output["text/plain"] = content["text"]
                elif msg_type == "error":
                    output["text/plain"] = "\n".join(content["traceback"])
                elif msg_type == "status":
                    state = content["execution_state"]
            except Empty:
                pass
            except KeyboardInterrupt:
                self.km.interrupt_kernel()
                break

        self.logger.debug("Code execution result: %s", output)

        return output

    def __del__(self):
        self.client.stop_channels()
        self.km.shutdown_kernel()


class CodeInterpreterListener(ChatListener):
    def __init__(self, function_name: str):
        self.session: Optional[CodeInterpreterSession] = None
        self.function_name = function_name

    def on_chat_clear(self):
        self.session = None

    def on_function_call(self, function_name: str, **kwargs) -> Optional[dict]:
        source = None
        if function_name == self.function_name:
            source = kwargs["source"]
        elif function_name == "pip_install":
            source = f"%pip install -qq --no-color {kwargs['package']}"

        if source:
            if self.session is None:
                self.session = CodeInterpreterSession()
            result = self.session.execute(source)
            if function_name == "pip_install":
                del self.session
                self.session = None
            return result
