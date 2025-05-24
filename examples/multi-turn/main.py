import threading

from fcan.server import A2AServer

def fetch_weather(location):
    url = f"https://wttr.in/{location}?T"

    import requests
    response = requests.get(url)
    response.raise_for_status()

    return response.text

skills = [{
    "id": "weather",
    "name": "Weather",
    "description": "Fetches the weather for a given location",
    "tags": ["weather"],
    "examples": [
        "What's the weather in Pune like tomorrow?.",
        "Tell me the temperature in Peru right now."
    ],
    "inputModes": ["text/plain"],
    "outputModes": ["application/json"]
}]

functions = [{
    "name": "fetch_weather",
    "description": "Returns the weather forecast for a given location using the wttr.in service for today and the next three days.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": { "type": "string" }                     
        },
        "required": ["location"]
    },
    "function": fetch_weather
}]


server = A2AServer(
    'Weather Agent',
    'Finds the weather for the given location.',
    'gemma3', skills, functions, port = 11420
)

server.start()
try:
    while True:
        threading.Event().wait(1)
except KeyboardInterrupt:
    print("\n! shutting down all servers")
