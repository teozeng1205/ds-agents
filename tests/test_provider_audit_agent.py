#!/usr/bin/env python3
"""
Ad-hoc end-to-end smoke tests for Provider Audit Agent.

Runs a few simple questions against the MCP-backed agent and prints outputs.
This is not a strict unit test; it exercises the full stack (OpenAI + MCP + Redshift).
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import Counter
from datetime import datetime

import importlib.util
from pathlib import Path
from agents import Runner


def _load_provider_agent():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "ds-agents" / "agents" / "provider_audit_agent.py"
    spec = importlib.util.spec_from_file_location("provider_audit_agent_module", mod_path)
    assert spec and spec.loader, f"Cannot load provider_audit_agent from {mod_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUESTIONS = [
    # Simple provider-only queries
    "AA has a recent increase in site-related issues. What are the top site issues in the last 7 days?",
    "For provider AA, what is the scope of site issues in the last 3 days? Focus on observation hour and POS only.",

    # Provider + sitecode (forces SQL fallback path)
    "Provider code QL2 with site code QF has an increase in site-related issues. What are the top site issues?",
    "Provider code QL2 with site code QF: Give a quick scope (observation hour and POS) in the last 3 days.",

    # A few more variations
    "For provider DL, list the top site-related issues in the past 7 days.",
    "Provider UA quick scope in last 3 days (observation hour and POS).",
]


async def main() -> None:
    print(f"Start: {datetime.utcnow().isoformat()}Z\n")

    # Make sure OpenAI key present
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set in environment; ensure your shell loads it.")

    agent_mod = _load_provider_agent()
    run_once = agent_mod.run_once

    for i, q in enumerate(QUESTIONS, start=1):
        print("=" * 80)
        print(f"Q{i}: {q}")
        try:
            t0 = time.perf_counter()
            # Detailed run to gather stats
            result = None
            out = ""
            try:
                from agents.mcp import MCPServerStdio, create_static_tool_filter
                # Use env.sh-first wrapper and new combined scope tool
                script = str((Path(__file__).resolve().parents[2] / 'ds-agents' / 'scripts' / 'run_mcp_provider_audit_stdio.sh'))
                allowed_tools = ["top_site_issues", "issue_scope_combined", "get_table_schema"]
                async with MCPServerStdio(
                    name="Provider Combined Audit (stdio)",
                    params={"command": "bash", "args": [script]},
                    cache_tools_list=True,
                    client_session_timeout_seconds=180.0,
                    tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
                ) as server:
                    agent = agent_mod.build_agent(server)
                    result = await Runner.run(agent, input=q)
                    out = result.final_output or ""
            except Exception:
                # Fallback to minimal run
                out = await run_once(q)
            t1 = time.perf_counter()

            # Output preview
            preview = out.strip()
            if len(preview) > 1200:
                preview = preview[:1200] + "\n... (truncated)"
            print("\nAnswer:\n" + (preview or "<no output>"))

            # Stats
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
