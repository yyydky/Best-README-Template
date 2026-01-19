# Minimal LangChain + FastMCP + Bedrock Demo

This demo wires together:
1) A LangChain agent with a "report portal" personality system prompt layer.
2) A FastMCP server exposing simple tools.
3) MCP prompt-based skills that guide tool usage.

The MCP server is spawned automatically via stdio by `MultiServerMCPClient`.

## Project structure

```
demo/
  server/
    ps_mcp_server.py
    state.py
  agent/
    run_agent.py
    rp_personality.py
  requirements.txt
  README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set environment variables:

```bash
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
# AWS credentials assumed to be available in your environment
```

## Run the agent

```bash
python agent/run_agent.py
```

## What to expect

- The agent fetches the MCP skill prompt and injects it as a system message.
- The agent calls MCP tools to build a minimal report state.
- `render_report` returns a dummy artifact string like `report://<id>.pdf`.
