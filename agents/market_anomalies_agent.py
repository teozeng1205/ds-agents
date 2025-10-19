#!/usr/bin/env python3
"""
Market Anomalies Agent

Creates an agent (OpenAI Agents SDK) that connects to the ds-mcp Market
Anomalies MCP server via stdio and answers anomaly questions.

Usage:
  python -m ds-agents.agents.market_anomalies_agent "your question"

Best practices used:
- MCPServerStdio lifecycle as async context manager
- Prefer MCP tools; fall back to SQL via query_anomalies with {{MLA}} macro
- Minimal, composable design
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStdio, create_static_tool_filter
from dsagents.mcp_agents import MarketAnomaliesMCPAgent


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ds_mcp_script_path() -> str:
    # Unified launcher used by OOP agent; chat.py uses the same
    return str(repo_root() / "ds-mcp" / "scripts" / "run_mcp_server.sh")


def build_agent(mcp_server: MCPServerStdio) -> Agent:
    """Backwards-compatible builder using the OOP wrapper."""
    return MarketAnomaliesMCPAgent().build(mcp_server)


async def run_once(question: str) -> str:
    agent_oop = MarketAnomaliesMCPAgent()
    async with agent_oop.create_mcp_server() as server:
        agent = agent_oop.build(server)
        result = await Runner.run(agent, input=question)
        return result.final_output or ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the Market Anomalies Agent")
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to ask the agent. If omitted, runs a small demo.",
    )
    args = parser.parse_args(argv)

    if args.question:
        question = " ".join(args.question)
        print(asyncio.run(run_once(question)))
        return 0

    # Demo flow for two example questions
    demo_q1 = (
        "Which customers have the most anomalies today? Then show a quick CP distribution."
    )
    demo_q2 = (
        "For customer B6 on 20251014, list top anomalies by impact_score and show a few markets."
    )

    print("Q1:", demo_q1)
    print(asyncio.run(run_once(demo_q1)))
    print()
    print("Q2:", demo_q2)
    print(asyncio.run(run_once(demo_q2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
