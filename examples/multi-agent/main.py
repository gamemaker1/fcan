from operator import mul
from functools import reduce

from fcan.server import A2AServer
from fcan.utils import wait_for_servers

def calculate_sum(numbers):
    return sum(numbers)

def calculate_product(numbers):
    return reduce(mul, numbers)

def calculate_average(numbers):
    return sum(numbers) / len(numbers)

math_skills = [{
    "id": "basic_maths",
    "name": "Basic Maths",
    "description": "Performs basic mathematical operations like addition, multiplication, calculating averages, etc.",
    "tags": ["math", "calculator"],
    "examples": [
        "Calculate the average of the following numbers - 2, 4, 5, 9.",
        "What's the product of 561 and 348? Find the average of the product and 32124 and 81339."
    ],
    "inputModes": ["text/plain"],
    "outputModes": ["text/markdown"]
}]

math_functions = [
    {
        "name": "calculate_sum",
        "description": "Finds the sum of a given list of numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": { "type": "number" }
                }                     
            }
        },
        "function": calculate_sum
    },
    {
        "name": "calculate_product",
        "description": "Finds the product of a given list of numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": { "type": "number" }
                }                     
            }
        },
        "function": calculate_product
    },
    {
        "name": "calculate_average",
        "description": "Finds the average of a given list of numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": { "type": "number" }
                }                     
            }
        },
        "function": calculate_average
    }
]

def fetch_weather(location):
    url = f"https://wttr.in/{location}?T"

    import requests
    response = requests.get(url)
    response.raise_for_status()

    return response.text

weather_skills = [{
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

weather_functions = [{
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

weather_skills = [{
    "id": "weather",
    "name": "Weather",
    "description": "Fetches the weather for a given place",
    "tags": ["weather"],
    "examples": [
        "What's the weather in Pune like tomorrow?.",
        "Tell me the temperature in Peru right now."
    ],
    "inputModes": ["text/plain"],
    "outputModes": ["application/json"]
}]

weather_functions = [{
    "name": "fetch_weather",
    "description": "Returns the weather forecast for a given place.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Must be the name of a place (city, town, etc.)."
            }
        },
        "required": ["location"]
    },
    "function": fetch_weather
}]

agents = [
    A2AServer(
        'Mathematical Agent',
        'Performs basic mathematical operations.',
        'gemma3', math_skills, math_functions, port = 11421
    ),
    A2AServer(
        'Weather Agent',
        'Finds the weather for the given location.',
        'gemma3', weather_skills, weather_functions, port = 11422
    ),
]

for agent in agents:
    agent.start()

wait_for_servers()
