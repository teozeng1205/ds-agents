#!/usr/bin/env python3
"""
Ad-hoc end-to-end smoke tests for Market Anomalies Agent.

Runs a couple of questions against the MCP-backed agent and prints outputs.
This exercises the full stack (OpenAI + MCP + Redshift). Not a strict unit test.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
import importlib.util

from agents import Runner


def _load_anomalies_agent():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "ds-agents" / "agents" / "market_anomalies_agent.py"
    spec = importlib.util.spec_from_file_location("market_anomalies_agent_module", mod_path)
    assert spec and spec.loader, f"Cannot load market_anomalies_agent from {mod_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUESTIONS = [
    "Which customers have the most anomalies today? Then show a quick CP distribution.",
    "For customer B6 on 20251014, list top anomalies by impact_score and show a few markets.",
]


async def main() -> None:
    print(f"Start: {datetime.utcnow().isoformat()}Z\n")

    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set in environment; ensure your shell loads it.")

    agent_mod = _load_anomalies_agent()
    run_once = agent_mod.run_once

    for i, q in enumerate(QUESTIONS, start=1):
        print("=" * 80)
        print(f"Q{i}: {q}")
        try:
            t0 = time.perf_counter()
            from agents.mcp import MCPServerStdio, create_static_tool_filter
            script = str((Path(__file__).resolve().parents[2] / 'ds-mcp' / 'scripts' / 'run_mcp_server.sh'))
            allowed_tools = [
                "query_anomalies",
                "get_table_schema",
                "get_available_customers",
                "overview_anomalies_today",
            ]
            result = None
            out = ""
            try:
                async with MCPServerStdio(
                    name="Market Anomalies (stdio)",
                    params={"command": "bash", "args": [script, 'anomalies']},
                    cache_tools_list=True,
                    client_session_timeout_seconds=180.0,
                    tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
                ) as server:
                    agent = agent_mod.build_agent(server)
                    result = await Runner.run(agent, input=q)
                    out = result.final_output or ""
            except Exception:
                out = await run_once(q)
            t1 = time.perf_counter()

            preview = out.strip()
            if len(preview) > 1200:
                preview = preview[:1200] + "\n... (truncated)"
            print("\nAnswer:\n" + (preview or "<no output>"))

            duration = t1 - t0
            tools = []
            token_in = token_out = total_tokens = 0
            if result is not None:
                for item in result.new_items:
                    raw = getattr(item, 'raw_item', None)
                    name = getattr(raw, 'name', None)
                    if name:
                        tools.append(name)
                for resp in result.raw_responses:
                    if resp.usage:
                        token_in += getattr(resp.usage, 'input_tokens', 0) or 0
                        token_out += getattr(resp.usage, 'output_tokens', 0) or 0
                        total_tokens += getattr(resp.usage, 'total_tokens', 0) or 0

            print("\nStats:")
            print(f"- Duration: {duration:.2f}s")
            print(f"- Tools used: {dict(Counter(tools)) if tools else '(none or not captured)'}")
            print(f"- Tokens: in={token_in}, out={token_out}, total={total_tokens}" if total_tokens else "- Tokens: (unavailable)")
        except Exception as e:
            print(f"\nERROR: {e}")
        print()

    print(f"Done: {datetime.utcnow().isoformat()}Z")


if __name__ == "__main__":
    asyncio.run(main())
