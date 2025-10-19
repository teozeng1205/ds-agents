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
        # Concrete subclasses declare server_kind: "provider" or "anomalies"
        server_kind = getattr(self, "server_kind", None)
        if not server_kind:
            raise RuntimeError("server_kind not set on agent; expected 'provider' or 'anomalies'")
        return MCPServerStdio(
            name=self.get_server_name(),
            params={"command": "bash", "args": [script, server_kind], "env": {"PYTHON": sys.executable}},
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
    server_kind = "provider"
    allowed_tools = (
        "query_audit",
        "get_table_schema",
        "top_site_issues",
        "issue_scope_combined",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Provider Combined Audit agent. Default to using query_audit with SQL macros.\n"
            "Prefer the issue_scope_combined tool when the user asks for multi-dimension scope (obs_hour/POS/triptype/LOS/OD/cabin/depart periods).\n\n"
            "Guidance:\n"
            "- Use sales_date (YYYYMMDD int) for time filters and partition pruning.\n"
            "- For site issues, select COALESCE(issue_reasons, issue_sources) as issue_key and filter out empty values.\n"
            "- For scope, call issue_scope_combined with dims like ['obs_hour','pos','triptype','los'] and provider/site.\n"
            "- For today vs usual (7-day average), compute via sales_date; avoid casting timestamps for coarse date filters.\n"
            "- Keep answers concise with clear bullets; order by importance.\n"
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        # Unified server launcher
        return Path(__file__).resolve().parents[2] / "ds-mcp" / "scripts" / "run_mcp_server.sh"


class MarketAnomaliesMCPAgent(BaseMCPAgent):
    name = "Market Anomalies (stdio)"
    server_kind = "anomalies"
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
        # Unified server launcher
        return Path(__file__).resolve().parents[2] / "ds-mcp" / "scripts" / "run_mcp_server.sh"


__all__ = [
    "BaseMCPAgent",
    "ProviderAuditMCPAgent",
    "MarketAnomaliesMCPAgent",
]
