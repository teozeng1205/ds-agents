# ds_agents

Python package that holds the analytics MCP agent definitions used by both the CLI (`chat.py`) and the ds-chat backend.  
Each agent configures a Model Context Protocol (MCP) server connection plus instructions, safety rails, and tool allow‑lists for a particular workflow.

## Package Overview

```
ds_agents/
├── __init__.py
└── mcp_agents/
    ├── base.py          # BaseMCPAgent scaffold
    └── generic.py       # GenericDatabaseMCPAgent definition
```

- **`BaseMCPAgent`** centralizes MCP server spawning, tool filtering, and agent construction.
- **`GenericDatabaseMCPAgent`** configures the shared “Database Explorer (stdio)” experience with provider monitoring instructions and helper tools.

## Installation

```bash
cd ds-agentic-workflows/ds-agents
python -m venv .venv && source .venv/bin/activate
pip install -U openai-agents
pip install -e .
```

When working inside the parent repo you can skip installation—`agent_core.py` injects this directory onto `PYTHONPATH` automatically.

## Using the Agents

```python
from ds_agents.mcp_agents import GenericDatabaseMCPAgent
from agents import Runner

agent = GenericDatabaseMCPAgent(common_tables=["prod.monitoring.provider_combined_audit"])
async with agent.create_mcp_server() as server:
    runner_agent = agent.build(server)
    result = await Runner.run(runner_agent, input="Show top site issues for QL2.")
    print(result.final_output)
```

The same agent is automatically wired into:
- `chat.py` (interactive CLI)
- `backend/agent_runner.py` in the ds-chat FastAPI service

## Extending

1. **Subclass `BaseMCPAgent`.** Override `name`, `instructions`, and `get_wrapper_script()` for your specific workflow.
2. **Expose additional tools.** Update `allowed_tools` or extend `ds-mcp` to publish new MCP tool definitions, then include them via `allowed_tool_names()`.
3. **Tune model settings.** Adjust `self.model_settings` for temperature, reasoning effort, etc.

Ship the new agent by importing it wherever `GenericDatabaseMCPAgent` is currently referenced.
