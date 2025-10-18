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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ds_mcp_script_path() -> str:
    # Use the env.sh-first wrapper which configures env + serialized SSO
    return str(repo_root() / "ds-agents" / "scripts" / "run_mcp_market_anomalies_stdio.sh")


def build_agent(mcp_server: MCPServerStdio) -> Agent:
    instructions = (
        "You are the Market Anomalies agent. Default to using query_anomalies with SQL macros.\n"
        "Only use other tools when explicitly asked (e.g., quick today overview or schema).\n\n"
        "Guidance:\n"
        "- Default: write a SELECT (or WITH) using {{MLA}} and call query_anomalies.\n"
        "- Keep answers concise with clear bullets; order by importance.\n\n"
        "Macros: {{MLA}} expands to analytics.market_level_anomalies_v3.\n\n"
        "Examples:\n"
        "- Top anomalies by impact for a customer/date:\n"
        "  SELECT seg_mkt, cp, impact_score FROM {{MLA}}\n"
        "  WHERE customer = '{customer}' AND sales_date = {sales_date} AND any_anomaly = 1\n"
        "  ORDER BY impact_score DESC LIMIT 20;\n"
        "- Daily anomaly counts per customer:\n"
        "  SELECT customer, sales_date, COUNT(*) cnt FROM {{MLA}} WHERE any_anomaly=1\n"
        "  GROUP BY customer, sales_date ORDER BY sales_date DESC LIMIT 50;\n"
    )

    model_settings = ModelSettings(temperature=0.2)

    return Agent(
        name="Market Anomalies Agent",
        instructions=instructions,
        mcp_servers=[mcp_server],
        model_settings=model_settings,
    )


async def run_once(question: str) -> str:
    script = ds_mcp_script_path()
    if not os.path.exists(script):
        raise RuntimeError(f"Could not find MCP script at: {script}")

    allowed_tools = [
        "query_anomalies",   # default macro SQL tool
        "get_table_schema",  # allow schema lookups
    ]

    async with MCPServerStdio(
        name="Market Anomalies (stdio)",
        params={
            "command": script,
            "args": [],
        },
        cache_tools_list=True,
        client_session_timeout_seconds=180.0,
        tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
    ) as server:
        agent = build_agent(server)
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
