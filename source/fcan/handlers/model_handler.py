"""
fcan/handlers/model_handler.py
==============================

handles all a2a methods using the model via ollama.
"""

import re
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
                You are {name}, an agent designed to complete tasks using your skills and function-calling abilities.
                Purpose: {description}
                Current UTC: {datetime.now(tz=timezone.utc).isoformat()}

                SKILLS:
                {json.dumps(skills, indent=2)}  
                FUNCTIONS:
                {json.dumps(specs, indent=2)}

                CRITICAL DIRECTIVES – READ CAREFULLY:
                1. Your responses MUST be VALID JSON.
                2. Use ONLY ONE of the three response formats given below.
                3. BEFORE CALLING A FUNCTION, ASK YOURSELF:
                   a. Do I have ALL REQUIRED PARAMETERS? If NO, go to (c).
                   b. Am I ASSUMING ANYTHING not given (e.g., location, preferences, time)? If YES, go to (c).
                   c. Do NOT call the function. First, you MUST use the REQUEST INFO response format to ask the user
                      a specific question. Check if (a) and (b) are satisfied. If YES, then call the function.
                4. You have NO EXTERNAL KNOWLEDGE OR SENSORS. Only use info from the conversation or available tools.

                RESPONSE FORMATS:

                1. FUNCTION CALL:
                {{ "function": "FUNCTION_NAME", "arguments": {{ "param1": "value1" }} }}

                2. REQUEST INFO:
                {{ "interrupt": "input", "message": "Ask user for specific missing info." }}

                3. FINAL ANSWER:
                {{
                  "response": "Optional message to user.",
                  "artifacts": [
                    [{{ "kind": "text", "content": "Text content" }}, {{ "kind": "data", "content": {{ "key": "value" }} }}],
                    [{{ "kind": "file", "content": {{ "name": "file.ext", "mime": "type", "bytes": "BASE64" }} }}]
                  ]
                }}

                "artifacts" is OPTIONAL if "response" is given, but ONE OR THE OTHER MUST BE PRESENT. 
                For "kind": "data", the "content" MUST BE A JSON OBJECT, NOT A STRING.
                "artifacts" MUST ALWAYS BE AN ARRAY OF ARRAYS.
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
        rpc_version = rpc.get("jsonrpc")
        request_id = rpc.get("id")

        if rpc_version != "2.0" or not request_id:
            return { "code": -32600, "message": "Invalid RPC request." }

        def responsify(content):
            return {
                "jsonrpc": rpc_version,
                "id": request_id,
                "result": content
            }

        method = rpc.get("method")
        params = rpc.get("params")

        if not method or not params:
            return responsify({ "code": -32600, "message": "Invalid RPC request." })

        if method == "discovery":
            return responsify(self.agent_card)

        if method == "message/send":
            message = params.get("message")
            message["id"] = params.get("messageId")
            task_id = params.get(
                "taskId", # add on to an existing task
                self.task_handler.create_task()["id"]
            )

            task = self.task_handler.get_task(task_id)
            if not task:
                return responsify({ "code": -32001, "message": "Task not found." })

            if task["status"]["state"] == "submitted":
                self.task_handler.update_task(task_id, "working")

            self.task_handler.store_message(task_id, message)
            return responsify(self.process_task(task_id))

        if method == "tasks/get":
            task_id = params.get("id")
            task = self.task_handler.get_task(task_id)
            if not task:
                return responsify({ "code": -32001, "message": "Task not found." })

            length = params.get("historyLength")
            history = self.task_handler.get_messages_for_task(task_id)
            task["history"] = history[:length]

            return responsify(task)

        return responsify({ "code": -32601, "message": "Method not found." })

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
        message = self.task_handler.store_message(task_id, {
            "role": "assistant",
            "parts": [{ "kind": "text", "text": content }]
        })

        try:
            content = content.strip()
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                content = match.group(1)
            call = json.loads(content)
        except Exception:
            print("! failed to parse model response")
            print(content)
            raise Exception("Invalid response.")

        if call.get("interrupt") == "input":
            print("i agent requires more input")
            self.task_handler.update_task(task_id, "input-required")

            task = { "kind": "task", "history": messages[:-1], **task }
            task["status"]["message"] = {
                "role": "assistant",
                "parts": [{ "kind": "text", "text": call["message"] }]
            }

            return task

        if call.get("function") is not None:
            print(f"i calling function {call["function"]}")
            output = self.functions[call["function"]](**call["arguments"])

            # gemma3 specifically does not support the `tool` role. instead, the instructions
            # must be part of the system and user prompts. see the message linked here:
            # https://huggingface.co/google/gemma-3-27b-it/discussions/8#67d4654e9c31239e1fc645dc
            self.task_handler.store_message(task_id, {
                "role": "user",
                "parts": [{
                    "kind": "text",
                    "text": dedent(f"""\
                        The output of the function call to {call["function"]} is given below the triple dash.

                        ---
                        {str(output)}
                    """.strip("\n"))
                }]
            })

            return self.process_task(task_id)

        if call.get("response") or call.get("artifacts"):
            task = self.task_handler.update_task(task_id, "completed")
            if call.get("response") is not None:
                message = self.task_handler.store_message(task_id, {
                    "role": "assistant",
                    "parts": [{ "kind": "text", "text": call["response"] }]
                })
                task["status"]["message"] = message

            if call.get("artifacts") is not None:
                task["artifacts"] = [{
                    "artifactId": self.task_handler.generate_id(),
                    "parts": artifact
                } for artifact in call["artifacts"]]

            task = { "kind": "task", "history": messages[:-1], **task }
            return task

        print("! llm returned invalid response")
        print(content)

        raise Exception("oops!")
