# Function Calling A2A Network

> A framework that empowers Ollama LLM agents in A2A networks with function calling.

## Overview

In its current state, this project is a prototype that tries to make the most
of function calling in A2A agents. It implements the A2A protocol (minus stuff
like streaming responses and input/output negotiation), and sets up LLM agents
with system prompts that enable function calling.

Currently, the prompts for the LLM agents have been written and tested with
Gemma 3 models (4B and 27B) running offline with [`ollama`](https://github.com/ollama/ollama)
to talk to the LLMs, it should be easy to add support for other models in the
future.

The next steps for this project involve adding an orchestration agent, which
discovers and delegates tasks to the correct agents based on their skills as
advertised in their agent cards. This agent may be an `A2AServer` itself, and
the delegation of tasks may be done via function calls.

## Getting Started

To get started with this, clone the repository:

```bash
git clone https://github.com/gamemaker1/fcan
```

The project uses [`mise`](https://github.com/jdx/mise) for tools and
[`uv`](https://github.com/astral-sh/uv) for package management. If you do not
have `mise` installed, make sure you have the tools in [`mise.toml`](mise.toml)
installed on your system.

Make sure you also have [`ollama`](https://github.com/ollama/ollama) up and
running on your machine, with the `gemma3` model downloaded.

## Examples

> The instructions for running the examples are given in the respective readmes.

The [`multi-turn`](examples/multi-turn) example demonstrates how a multi-turn
conversation with an agent takes place via the A2A protocol, with the agent
making use of the functions provided to it and requesting input from the user
when it is not provided.

The [`multi-agent`](examples/multi-agent) example demonstrates how to setup
and run multiple agents on different ports. It is incomplete, since it needs
an orchestration agent to tie it all together.
