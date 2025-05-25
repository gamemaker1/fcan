"""
fcan/handlers/task_handler.py
==============================

manages tasks and their messages for the agent.
"""

import json

from textwrap import dedent
from datetime import datetime, timezone
from ulid import ULID

class TaskHandler:
    """
    manages tasks and their messages.
    """

    def __init__(self):
        self.tasks = {}
        self.messages = {}

    @staticmethod
    def generate_id():
        ulid = ULID()
        return ulid.hex

    @staticmethod
    def get_timestamp():
        return datetime.now(tz = timezone.utc).isoformat()

    @staticmethod
    def valid_states():
        return [
          "unknown", "submitted", "working",
          "completed", "failed", "canceled", "rejected",
          "input-required", "auth-required"
        ]

    @staticmethod
    def working_states():
        return ["working", "input-required", "auth-required"]

    def create_task(self, metadata = None):
        task_id = self.generate_id()
        task = {
            "id": task_id,
            "status": {
                "state": "submitted",
                "timestamp": self.get_timestamp()
            },
            "metadata": metadata
        }

        self.tasks[task_id] = task
        return task

    def get_task(self, task_id):
        if task_id not in self.tasks:
            return None

        return self.tasks[task_id]

    def update_task(self, task_id, state):
        if state not in self.valid_states():
            return None

        if task_id not in self.tasks:
            return None

        self.tasks[task_id]["status"] = {
            "state": state,
            "timestamp": self.get_timestamp()
        }

        return self.tasks[task_id]

    def store_message(self, task_id, message):
        if task_id not in self.messages:
            self.messages[task_id] = []

        if not message.get("id"):
            message["id"] = self.generate_id()

        self.messages[task_id].append(message)
        return message

    def get_message(self, task_id, message_id):
        if task_id not in self.messages:
            return None

        for message in self.messages[task_id]:
            if message["id"] == message_id:
                return message

        return None

    def get_messages_for_task(self, task_id):
        if task_id not in self.messages:
            return None

        return self.messages[task_id]

    def get_conversation_for_task(self, task_id):
        history = self.get_messages_for_task(task_id) or []
        messages = []

        for message in history:
            role = message.get("role", "user")
            kind = message.get("parts", [])[0].get("kind")

            # ignore the assistant's `data` messages.
            if role != "assistant" or kind != "data":
                messages.append(message)

        return messages

    def get_llm_history_for_task(self, task_id):
        history = self.get_messages_for_task(task_id) or []
        messages = []

        for message in history:
            role = message.get("role", "user")

            # from the assistant, we only want to include the
            # `data` messages, and all the user and tool messages.

            content = ""
            for part in message.get("parts", []):
                if part.get("kind") == "text" and role != "assistant":
                    content += str(part.get("text", ""))
                elif part.get("kind") == "data":
                    content += json.dumps(part.get("data", ""), indent = 4)
                else:
                    print("@ warning: skipped non-text part")

            if content == "":
                continue

            if role != "tool":
                messages.append({ "role": role, "content": content })
                continue

            # gemma3 specifically does not support the `tool` role. instead, the instructions
            # must be part of the system and user prompts. see the message linked here:
            # https://huggingface.co/google/gemma-3-27b-it/discussions/8#67d4654e9c31239e1fc645dc
            messages.append({
                "role": "user",
                "content": dedent(f"""\
                    The output of the function ({message.get("metadata", {}).get("function")}
                    is given below the triple dash.

                    ---
                    {str(content)}
                """.strip("\n"))
            })

        return messages
