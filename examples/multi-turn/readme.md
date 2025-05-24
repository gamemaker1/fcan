## Multi-Turn Example

First, make sure the Gemma 3 (4B) model is downloaded:

```bash
ollama serve &
ollama pull gemma3
```

To start the A2A agent server, run:

```bash
uv run examples/multi-turn/main.py
```

This runs a weather agent with a function that can fetch the weather for a
given location from [`wttr.in`](https://wttr.in).

The `message-0.json` file contains a JSON-RPC request object that sends a
message from the user asking what the weather is right now. To make this first
request, run:

```bash
curl -s -XPOST http://localhost:11420 \
  -H 'content-type: application/json' \
  -d@examples/multi-turn/message-0.json | jq
```

The agent should respond with a request for more data - specfically, the
location for which you want the weather. Open the `message-1.json` file
and edit the `"content"` key with the location you want it to answer for.
Also include the `taskId` from the agent's response, to ensure the current
conversation is continued.

To make this second request, run:

```bash
curl -s -XPOST http://localhost:11420 \
  -H 'content-type: application/json' \
  -d@examples/multi-turn/message-1.json | jq
```

It should respond with the current weather in the location you entered.
