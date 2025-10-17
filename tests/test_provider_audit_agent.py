#!/usr/bin/env python3
"""
Ad-hoc end-to-end smoke tests for Provider Audit Agent.

Runs a few simple questions against the MCP-backed agent and prints outputs.
This is not a strict unit test; it exercises the full stack (OpenAI + MCP + Redshift).
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime

import importlib.util
from pathlib import Path


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
    "For provider AA, what is the scope of site issues in the last 3 days? Focus on observation hour, POS, OD, cabin, depart periods.",

    # Provider + sitecode (forces SQL fallback path)
    "Provider code QL2 with site code QF has an increase in site-related issues. What are the top site issues?",
    "Provider code QL2 with site code QF: What is the scope of site issues across obs hour, POS, OD, cabin, depart periods in the last 3 days?",
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
            out = await run_once(q)
            print("\nAnswer:\n" + (out or "<no output>"))
        except Exception as e:
            print(f"\nERROR: {e}")
        print()

    print(f"Done: {datetime.utcnow().isoformat()}Z")


if __name__ == "__main__":
    asyncio.run(main())
