# agent-mcp

This is an agent using OpenAI LLM for answering user messages with MCP (Model Context Protocol) integration. This agent has no proper support for multiple sessions handling.

This example demonstrates how to create an agent with LLM integration and MCP server tools. For a more complete example, refer to [agent-extended](../agent-extended/README.md).

## Setup

1. Copy [sample.env](./sample.env) to [.env](./.env) and fill in the required values:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MODEL_NAME`: The model to use (e.g., gpt-4)
   - `MCP_SERVER_URL`: URL of your MCP server (default: http://localhost:8080)
   - `MCP_API_KEY`: Your MCP server API key (if required)



# Run

Copy [sample.env](./sample.env) to [.env](./.env) and fill in the required values.

Then run this agent with the following commands:

```bash
devbox shell
poetry install --no-root && poetry run python agent.py
```
