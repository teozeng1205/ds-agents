#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Sequence

from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStdio, create_static_tool_filter


class BaseMCPAgent:
    name: str = "MCP Agent"
    instructions: str = "Use configured tools to answer the user concisely."
    allowed_tools: Sequence[str] = ()
    client_session_timeout_seconds: float = 180.0

    def __init__(self, name: str | None = None, instructions: str | None = None):
        if name:
            self.name = name
        if instructions:
            self.instructions = instructions
        self.model_settings = ModelSettings(temperature=0.2)

    def get_wrapper_script(self) -> Path:
        raise NotImplementedError

    def get_server_name(self) -> str:
        return self.name

    def build(self, mcp_server: MCPServerStdio) -> Agent:
        return Agent(
            name=self.name,
            instructions=self.instructions,
            mcp_servers=[mcp_server],
            model_settings=self.model_settings,
        )

    def create_mcp_server(self) -> MCPServerStdio:
        script = str(self.get_wrapper_script())
        if not os.path.exists(script):
            raise RuntimeError(f"Wrapper script not found: {script}")
        return MCPServerStdio(
            name=self.get_server_name(),
            params={"command": "bash", "args": [script]},
            cache_tools_list=True,
            client_session_timeout_seconds=self.client_session_timeout_seconds,
            tool_filter=create_static_tool_filter(allowed_tool_names=list(self.allowed_tools)),
        )

    async def run_once(self, question: str) -> str:
        async with self.create_mcp_server() as server:
            agent = self.build(server)
            result = await Runner.run(agent, input=question)
            return result.final_output or ""


class ProviderAuditMCPAgent(BaseMCPAgent):
    name = "Provider Combined Audit (stdio)"
    allowed_tools = (
        "query_audit",
        "get_table_schema",
        "issue_scope_combined",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Provider Combined Audit agent. Default to using query_audit with SQL macros.\n"
            "Prefer the issue_scope_combined tool when the user asks for multi-dimension scope (obs_hour/POS/triptype/LOS/OD/cabin/depart periods).\n\n"
            "Guidance:\n"
            "- For site issues, select COALESCE(issue_reasons, issue_sources) as issue_key and filter out empty values.\n"
            "- For scope, call issue_scope_combined with dims like ['obs_hour','pos','triptype','los'] and provider/site.\n"
            "- Keep answers concise with clear bullets; order by importance.\n"
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[2] / "ds-agents" / "scripts" / "run_mcp_provider_audit_stdio.sh"


class MarketAnomaliesMCPAgent(BaseMCPAgent):
    name = "Market Anomalies (stdio)"
    allowed_tools = (
        "query_anomalies",
        "get_table_schema",
        "get_available_customers",
        "overview_anomalies_today",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Market Anomalies agent. Default to using query_anomalies with {{MLA}} macros.\n"
            "Use get_table_schema and overview_anomalies_today when asked for structure or today overview.\n\n"
            "Guidance:\n"
            "- Default: write a SELECT (or WITH) using {{MLA}} and call query_anomalies.\n"
            "- Keep answers concise with clear bullets; order by importance.\n"
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[2] / "ds-agents" / "scripts" / "run_mcp_market_anomalies_stdio.sh"


__all__ = [
    "BaseMCPAgent",
    "ProviderAuditMCPAgent",
    "MarketAnomaliesMCPAgent",
]

