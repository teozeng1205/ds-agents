#!/usr/bin/env python3
"""
Provider Combined Audit Agent

Creates an agent (OpenAI Agents SDK) that connects to the ds-mcp Provider Combined Audit MCP
server via stdio and answers provider audit questions.

Usage:
  python -m ds-agents.agents.provider_audit_agent "your question"

Best practices used:
- MCPServerStdio lifecycle as async context manager
- Prefer MCP tools; fall back to SQL via query_audit macros when needed
- Minimal, composable design ready for more agents/handoffs later
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStdio


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ds_mcp_script_path() -> str:
    # Use the ds-mcp stdio run script which configures env + .venv
    return str(repo_root() / "ds-mcp" / "scripts" / "run_provider_combined_audit.sh")


def build_agent(mcp_server: MCPServerStdio) -> Agent:
    instructions = (
        "You are the Provider Combined Audit agent. Use the MCP tools from the connected server\n"
        "to analyze provider monitoring events for site-related issues.\n\n"
        "Guidance:\n"
        "- Prefer calling built-in tools: top_site_issues(provider, lookback_days),\n"
        "  issue_scope_breakdown(provider, lookback_days, per_dim_limit).\n"
        "- If a site code filter is explicitly requested (e.g., sitecode='QF'), use query_audit\n"
        "  and filter BOTH providercode and sitecode with ILIKE, plus {{IS_SITE}}.\n"
        "- Use date window defaults of 7 days unless user asks otherwise.\n"
        "- Keep answers concise and structured with clear bullets.\n\n"
        "Macros available to query_audit: {{PCA}}, {{OD}}, {{ISSUE_TYPE}}, {{EVENT_TS}},\n"
        "{{OBS_HOUR}}, {{IS_SITE}}, {{IS_INVALID}}.\n\n"
        "Top site issues via SQL (fallback example):\n"
        "SELECT COALESCE(NULLIF(TRIM(issue_reasons::VARCHAR), ''), NULLIF(TRIM(issue_sources::VARCHAR), ''), 'unknown') AS issue_key,\n"
        "       COUNT(*) AS cnt\n"
        "FROM {{PCA}}\n"
        "WHERE providercode ILIKE '%{provider}%' AND sitecode ILIKE '%{site}%'\n"
        "  AND {{IS_SITE}}\n"
        "  AND TO_DATE(scheduledate::VARCHAR, 'YYYYMMDD') >= CURRENT_DATE - {lookback}\n"
        "GROUP BY 1 ORDER BY 2 DESC LIMIT {limit};\n\n"
        "Scope via SQL (fallback patterns if needed):\n"
        "- obs_hour: SELECT DATE_TRUNC('hour', {{EVENT_TS}}) AS bucket, COUNT(*) ... GROUP BY 1 ORDER BY 2 DESC\n"
        "- pos: SELECT NULLIF(TRIM(pos::VARCHAR), '') AS bucket, COUNT(*) ...\n"
        "- od: SELECT (originairportcode || '-' || destinationairportcode) AS bucket, COUNT(*) ...\n"
        "- cabin: SELECT NULLIF(TRIM(cabin::VARCHAR), '') AS bucket, COUNT(*) ...\n"
        "- depart_week: SELECT DATE_TRUNC('week', TO_DATE(departdate::VARCHAR, 'YYYYMMDD')) AS bucket, COUNT(*) ...\n"
    )

    # Ask the model to choose tools when relevant; keep the temperature low
    model_settings = ModelSettings(temperature=0.2)

    return Agent(
        name="Provider Audit Agent",
        instructions=instructions,
        mcp_servers=[mcp_server],
        model_settings=model_settings,
    )


async def run_once(question: str) -> str:
    script = ds_mcp_script_path()
    if not os.path.exists(script):
        raise RuntimeError(f"Could not find MCP script at: {script}")

    async with MCPServerStdio(
        name="Provider Combined Audit (stdio)",
        params={
            "command": script,
            "args": [],
        },
        cache_tools_list=True,
    ) as server:
        agent = build_agent(server)
        result = await Runner.run(agent, input=question)
        return result.final_output or ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the Provider Audit Agent")
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

    # Demo flow for the two example questions
    demo_q1 = (
        "Provider code QL2 with site code QF had an increase in site-related issues recently. "
        "What are the top site issues in the last 7 days?"
    )
    demo_q2 = (
        "Provider code QL2 with site code QF: What is the scope of the issue? "
        "Focus on obs hour, POS, OD, cabin, and depart periods."
    )

    print("Q1:", demo_q1)
    print(asyncio.run(run_once(demo_q1)))
    print()
    print("Q2:", demo_q2)
    print(asyncio.run(run_once(demo_q2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

