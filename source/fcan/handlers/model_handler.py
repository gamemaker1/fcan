"""
fcan/handlers/model_handler.py
==============================

handles all a2a methods using the model via ollama.
"""

import json

from textwrap import dedent
from datetime import datetime, timezone
from ollama import Client

from fcan.handlers import TaskHandler

class ModelHandler:
    """
    handles all a2a methods using the model via ollama.
    """

    def __init__(
        self,
        name, description, model,
        skills, functions,
        ollama_url, endpoint,
        version = "0.1.0"
    ):
        specs, calls = self.load_functions(functions)
        self.functions = calls

        self.model = model
        self.llm = Client(host = ollama_url)
        self.prompt = {
            "content": dedent(f"""\
                You are an agent with the following name and description:

                {name} - {description}

                The current date and time (UTC) is {datetime.now(tz = timezone.utc).isoformat()}

                You can call upon the following set of functions. You MUST NOT call a function if a
                function parameter is required and cannot be determined from the user's message. In
                such a case, you MUST request the user for more information instead by responding with
                the following in plain text ONLY ONCE:

                {{"blocking": "input", "message": the message for the user}}

                The following is the list of functions:

                {json.dumps(specs, indent = 4)}

                To call any one of these functions, you MUST respond with the following in plain text:

                {{"function": function name, "parameters": dictionary of argument name and its value}}

                IMPORTANT: all argument values must be literals, not expressions. You SHOULD NOT include
                any other text in the response if you call a function.

                You MUST call only function in one turn. Once you have called all the functions, use the
                conversation history and present ONLY the relevant portion of the output(s) as requested
                by the user in a single, user-friendly message. You MUST phrase the message as a response
                to the user's request.
            """.strip("\n")),
            "role": "system"
        }

        self.agent_card = {
            "protocol": "a2a-1.0",
            "version": version,
            "name": name,
            "description": description,
            "skills": skills,
            "url": endpoint
        }

        self.task_handler = TaskHandler()

    def load_functions(self, functions):
        specs, calls = [], {}
        for func in functions:
            calls[func["name"]] = func["function"]
            func.pop("function")
            specs.append(func)

        return specs, calls

    def process_request(self, rpc):
        method = rpc.get("method")
        params = rpc.get("params")

        if not method or not params:
            return { "code": -32600, "message": "Invalid RPC request." }

        if method == "discovery":
            return self.agent_card

        if method == "message/send":
            message = params.get("message")
            message["id"] = params.get("messageId")
            task_id = params.get(
                "taskId", # add on to an existing task
                self.task_handler.create_task()["id"]
            )

            task = self.task_handler.get_task(task_id)
            if task["status"]["state"] == "submitted":
                self.task_handler.update_task(task_id, "working")

            self.task_handler.store_message(task_id, message)
            return self.process_task(task_id)

        if method == "tasks/get":
            task_id = params.get("id")
            task = self.task_handler.get_task(task_id)
            if not task:
                return { "code": -32001, "message": "Task not found." }

            length = params.get("historyLength")
            history = self.task_handler.get_messages_for_task(task_id)
            task["history"] = history[:length]

            return task

        return { "code": -32601, "message": "Method not found." }

    def process_task(self, task_id):
        task = self.task_handler.get_task(task_id)
        if not task:
            return { "code": -32001, "message": "Task not found." }

        task_state = task.get("status", {}).get("state")
        if task_state not in self.task_handler.working_states():
            return task

        history = self.task_handler.get_history_for_task(task_id)
        messages = self.task_handler.get_messages_for_task(task_id)
        response = self.llm.chat(model = self.model, messages = [self.prompt, *history])
        content = response.get("message", {}).get("content")

        if content.startswith('{"blocking": "input"'):
            print("i agent requires more input")
            try:
                request = json.loads(content)
            except Exception:
                print("! failed to parse input request")
                print(content)

            self.task_handler.update_task(task_id, "input-required")

            message = self.task_handler.store_message(task_id, {
                "role": "assistant",
                "parts": [{ "kind": "text", "text": request["message"] }]
            })
            task["status"]["message"] = message
            task = { "kind": "task", "history": messages[:-1], **task }

            return task

        message = self.task_handler.store_message(task_id, {
            "role": "assistant",
            "parts": [{ "kind": "text", "text": content }]
        })

        if content.startswith('{"function":'):
            try:
                call = json.loads(content)
            except Exception:
                print("! failed to parse function call")
                print(content)

            print(f"i calling function {call["function"]}")
            output = self.functions[call["function"]](**call["parameters"])

            # gemma3 specifically does not support the `tool` role. instead, the instructions
            # must be part of the system and user prompts. see the message linked here:
            # https://huggingface.co/google/gemma-3-27b-it/discussions/8#67d4654e9c31239e1fc645dc
            self.task_handler.store_message(task_id, {
                "role": "user",
                "parts": [{
                    "kind": "text",
                    "text": dedent(f"""\
                        The output of the call to {call["function"]} is given below the triple dash.

                        ---
                        {str(output)}
                    """.strip("\n"))
                }]
            })

            return self.process_task(task_id)

        task = self.task_handler.update_task(task_id, "completed")
        message = self.task_handler.store_message(task_id, {
            "role": "assistant",
            "parts": [{ "kind": "text", "text": content }]
        })

        task["status"]["message"] = message
        task = { "kind": "task", "history": messages[:-1], **task }

        return task
