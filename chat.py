#!/usr/bin/env python3
"""
Interactive chat interface for Provider or Market Anomalies agents.

Defaults to SQL macro tools in all cases (query_audit / query_anomalies),
keeping the tool surface minimal and predictable. You can still call
get_table_schema for quick schema lookups.

Best practices used:
- Keep a single MCP stdio server process alive across turns.
- Manage multi‑turn conversation via RunResult.to_input_list() (manual conversation state).
- Filter MCP tools to a small, fast set (macro query + schema only by default).

Run:
  python ds-agents/chat.py --agent provider
  python ds-agents/chat.py --agent anomalies

Type '/exit' to quit.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections import Counter
import argparse
from pathlib import Path

from agents import Runner
from agents.mcp import MCPServerStdio, create_static_tool_filter


def _load_provider_agent_module():
    """Load the provider audit agent (no packaging required)."""
    import importlib.util

    mod_path = Path(__file__).resolve().parent / "agents" / "provider_audit_agent.py"
    spec = importlib.util.spec_from_file_location("provider_audit_agent_module", mod_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load provider_audit_agent from {mod_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_anomalies_agent_module():
    """Load the market anomalies agent (no packaging required)."""
    import importlib.util

    mod_path = Path(__file__).resolve().parent / "agents" / "market_anomalies_agent.py"
    spec = importlib.util.spec_from_file_location("market_anomalies_agent_module", mod_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load market_anomalies_agent from {mod_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def chat(agent_kind: str) -> int:
    # Resolve agent + MCP stdio script + default macro tools
    launcher = str((Path(__file__).resolve().parents[1] / "ds-mcp" / "scripts" / "run_mcp_server.sh"))
    if agent_kind == "anomalies":
        agent_mod = _load_anomalies_agent_module()
        allowed_tools = [
            "query_anomalies",   # default SQL macro tool
            "get_table_schema",
        ]
        server_name = "Market Anomalies (stdio)"
    else:
        agent_mod = _load_provider_agent_module()
        allowed_tools = [
            "query_audit",       # default SQL macro tool
            "get_table_schema",
            "issue_scope_combined",  # efficient multi-dimension scope in one query
        ]
        server_name = "Provider Combined Audit (stdio)"

    print(f"Starting MCP server for {agent_kind} …", file=sys.stderr)
    # Ensure the MCP server uses the same Python interpreter as this process
    server_env = {"PYTHON": sys.executable}

    async with MCPServerStdio(
        name=server_name,
        # Run unified ds-mcp server launcher with explicit kind argument
        params={"command": "bash", "args": [launcher, agent_kind], "env": server_env},
        cache_tools_list=True,
        client_session_timeout_seconds=180.0,
        tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
    ) as server:
        agent = agent_mod.build_agent(server)

        # Manual conversation management using to_input_list()
        # See: docs/running_agents.md → Manual conversation management
        conversation_items = None  # type: list | None

        print("Chat ready. Type /exit to quit.\n")
        while True:
            try:
                user = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return 0

            if not user:
                continue
            if user.lower() in {"/exit", ":q", ":quit", ":exit"}:
                print("Bye.")
                return 0

            # Build the input payload for this turn
            if conversation_items is None:
                input_payload = user
            else:
                # Append user message to prior items
                input_payload = list(conversation_items)
                input_payload.append({"role": "user", "content": user})

            t0 = time.perf_counter()
            result = await Runner.run(agent, input=input_payload)
            dt = time.perf_counter() - t0

            # Print final output
            final_text = (result.final_output or "").strip()
            print("Assistant:")
            print(final_text if final_text else "<no output>")

            # Lightweight stats (tools + tokens)
            tools = []
            for item in result.new_items:
                raw = getattr(item, "raw_item", None)
                name = getattr(raw, "name", None)
                if name:
                    tools.append(name)
            if tools:
                counts = dict(Counter(tools))
                print(f"[tools] {counts}")
            # Token usage (if available for this model/provider)
            total_in = total_out = total = 0
            for resp in result.raw_responses:
                if resp.usage:
                    total_in += getattr(resp.usage, "input_tokens", 0) or 0
                    total_out += getattr(resp.usage, "output_tokens", 0) or 0
                    total += getattr(resp.usage, "total_tokens", 0) or 0
            if total:
                print(f"[usage] in={total_in}, out={total_out}, total={total}")
            print(f"[time] {dt:.2f}s\n")

            # Update conversation state for next turn
            conversation_items = result.to_input_list()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive chat for provider or anomalies agents (macro-SQL first)")
    parser.add_argument("--agent", choices=["provider", "anomalies"], default="provider", help="Which agent to chat with")
    args = parser.parse_args()
    return asyncio.run(chat(args.agent))


if __name__ == "__main__":
    raise SystemExit(main())
