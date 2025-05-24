"""
fcan/server.py
==============

provides a json-rpc http server to handle a2a methods.
"""

import traceback
import logging
import threading
import flask.cli

from flask import Flask, request, jsonify

from fcan.handlers import ModelHandler

class A2AServer:
    """
    provides a json-rpc http server to handle a2a methods.
    """

    def __init__(
        self,
        name, description, model, skills, functions,
        host = "0.0.0.0", port = 11420,
        ollama_url = "http://localhost:11434"
    ):
        self.host, self.port = host, port
        self.endpoint = f"http://{host}:{port}"

        self.app = Flask(__name__)
        self.model_handler = ModelHandler(
            name, description, model,
            skills, functions,
            ollama_url, self.endpoint
        )

        self.setup()

    def setup(self):
        self.app.logger.disabled = True
        logging.getLogger('werkzeug').disabled = True
        flask.cli.show_server_banner = lambda *args: None

        @self.app.route("/.well-known/agent.json", methods=["GET"])
        def agent_card():
            return jsonify(self.model_handler.agent_card)

        @self.app.route("/", methods=["POST"])
        def rpc_handler():
            rpc = request.json
            print(f"- handling rpc request ({rpc.get("method", "unknown")})")

            try:
                response = self.model_handler.process_request(rpc)
                return jsonify(response)
            except Exception:
                print("! error handling request")
                print(traceback.format_exc())
                return jsonify({ "code": -32603, "message": "Internal error." })

    def start(self):
        print(f"> listening for rpc calls at port {self.port} on {self.host}")
        threading.Thread(target = self.app.run, args = (self.host, self.port), daemon = True).start()
