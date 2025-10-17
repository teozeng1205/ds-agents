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
from agents.mcp import MCPServerStdio, create_static_tool_filter


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ds_mcp_script_path() -> str:
    # Use the ds-mcp stdio run script which configures env + .venv
    return str(repo_root() / "ds-mcp" / "scripts" / "run_provider_combined_audit.sh")


def build_agent(mcp_server: MCPServerStdio) -> Agent:
    instructions = (
        "You are the Provider Combined Audit agent. Default to using query_audit with SQL macros.\n"
        "Prefer the issue_scope_combined tool when the user asks for multi-dimension scope (e.g., obs_hour/POS/triptype/LOS/OD/cabin/depart periods).\n\n"
        "Guidance:\n"
        "- Default: write a SELECT (or WITH) using macros and call query_audit.\n"
        "- For scope across dimensions in one query, call issue_scope_combined with dims like ['obs_hour','pos','triptype','los'] and provider/site.\n"
        "- Macros: {{PCA}} (table), {{ISSUE_TYPE}}, {{OD}}, {{EVENT_TS}}, {{OBS_HOUR}}, {{IS_SITE}}, {{IS_INVALID}}.\n"
        "- Keep outputs concise with clear bullets; order by importance.\n\n"
        "Examples:\n"
        "- Top site issues: SELECT {{ISSUE_TYPE}} AS issue_key, COUNT(*) cnt FROM {{PCA}}\n"
        "  WHERE providercode ILIKE '%{provider}%'\n"
        "    AND NULLIF(TRIM(issue_sources::VARCHAR), '') IS NOT NULL\n"
        "    AND TO_DATE(sales_date::VARCHAR,'YYYYMMDD') >= CURRENT_DATE - {days}\n"
        "  GROUP BY 1 ORDER BY 2 DESC LIMIT {limit};\n"
        "- Quick scope (obs_hour, pos) for provider+site: two queries with {{OBS_HOUR}} and pos.\n"
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

    allowed_tools = [
        "query_audit",           # default macro SQL tool
        "get_table_schema",      # allow schema lookups
        "issue_scope_combined",  # multi-dimension scope in one query
    ]

    async with MCPServerStdio(
        name="Provider Combined Audit (stdio)",
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
