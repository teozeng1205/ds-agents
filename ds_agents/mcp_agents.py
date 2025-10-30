#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Sequence

from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStdio, create_static_tool_filter


class BaseMCPAgent:
    name: str = "MCP Agent"
    instructions: str = "Use configured tools to answer the user concisely."
    # Canonical table tools shared by every ds-mcp table
    base_tools: Sequence[str] = ("query_table", "get_table_schema")
    # Subclasses can extend this with table-specific helpers or aliases
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
            tool_filter=create_static_tool_filter(allowed_tool_names=self.allowed_tool_names()),
        )

    async def run_once(self, question: str) -> str:
        async with self.create_mcp_server() as server:
            agent = self.build(server)
            result = await Runner.run(agent, input=question)
            return result.final_output or ""

    def allowed_tool_names(self) -> list[str]:
        """Return the combined list of canonical and table-specific tools."""
        names: dict[str, None] = {tool: None for tool in self.base_tools}
        for tool in self.allowed_tools:
            names.setdefault(tool, None)
        return list(names.keys())


class ProviderAuditMCPAgent(BaseMCPAgent):
    name = "Provider Combined Audit (stdio)"
    server_kind = "provider"
    allowed_tools = (
        "query_audit",
        "top_site_issues",
        "top_site_issues_flex",
        "issue_scope_combined",
        "issue_scope_combined_flex",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Provider Combined Audit agent.\n"
            "Workflow:\n"
            "1. Parse each request for provider, site, lookback window, and requested dimensions. Normalise provider/site codes to uppercase strings.\n"
            "2. Default path: run query_audit with safe SQL templates that use macros.\n"
            "   • Top site issues (replace PROVIDER_CODE and DAYS; do not add extra filters—zero rows means no recorded issues):\n"
            "     SELECT NULLIF(TRIM(sitecode::VARCHAR), '') AS site,\n"
            "            COALESCE(NULLIF(TRIM(issue_reasons::VARCHAR), ''), NULLIF(TRIM(issue_sources::VARCHAR), '')) AS issue_label,\n"
            "            COUNT(*) AS issue_count\n"
            "     FROM {{PCA}}\n"
            "     WHERE providercode = 'PROVIDER_CODE'\n"
            "       AND sales_date >= CAST(TO_CHAR(CURRENT_DATE - DAYS, 'YYYYMMDD') AS INT)\n"
            "     GROUP BY 1, 2\n"
            "     ORDER BY issue_count DESC\n"
            "     LIMIT 10;\n"
            "   • Scope breakdown (add/remove dims from {obs_hour,pos,od,cabin,triptype,los}; keep issue label and allow NULL/empty values):\n"
            "     SELECT {{EVENT_TS:obs_hour}},\n"
            "            NULLIF(TRIM(pos::VARCHAR), '') AS pos,\n"
            "            COALESCE(NULLIF(TRIM(issue_reasons::VARCHAR), ''), NULLIF(TRIM(issue_sources::VARCHAR), '')) AS issue_label,\n"
            "            COUNT(*) AS issue_count\n"
            "     FROM {{PCA}}\n"
            "     WHERE providercode = 'PROVIDER_CODE'\n"
            "       AND sitecode = 'SITE_CODE'\n"
            "       AND sales_date >= CAST(TO_CHAR(CURRENT_DATE - DAYS, 'YYYYMMDD') AS INT)\n"
            "     GROUP BY 1, 2, 3\n"
            "     ORDER BY issue_count DESC\n"
            "     LIMIT 10;\n"
            "   Substitute the correct provider/site, adjust DAYS/LIMIT, and extend the SELECT/GROUP BY clauses when additional dims are needed (triptype, los, od, cabin, depart periods, travel DOW, etc.).\n"
            "3. If a published tool meets the need, you may call the *_flex helpers; always include the original question in the \"request\" argument plus explicit provider/site when known (e.g., {\"tool\": \"top_site_issues_flex\", \"arguments\": {\"request\": \"Top site issues for provider QL2 last 3 days\", \"lookback_days\": 3, \"limit\": 10}}).\n"
            "4. After any tool call, parse the JSON string with json.loads. If it contains \"error\", report the failure succinctly. If row_count == 0, reply that no matching rows were found. Summaries must be concise bullet points that cite the tool (e.g., “- EXP: 83k issues (query_audit)”).\n"
            "5. Never reference the table directly—always rely on macros such as {{PCA}}, {{ISSUE_TYPE}}, and {{EVENT_TS:alias}}. Use single quotes for string literals.\n\n"
            "Data notes:\n"
            "- sales_date is INT YYYYMMDD; use CAST(TO_CHAR(CURRENT_DATE - N, 'YYYYMMDD') AS INT) for rolling windows.\n"
            "- Issue labels come from COALESCE(issue_reasons, issue_sources); report them even when NULL or empty to reflect missing root cause.\n"
            "- observationtimestamp / actualscheduletimestamp combine via COALESCE, then DATE_TRUNC('hour', ...) yields obs_hour.\n"
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
        "get_available_customers",
        "overview_anomalies_today",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Market Anomalies agent.\n"
            "Prefer the table-specific tools first:\n"
            "- get_available_customers(limit=...) for customer counts.\n"
            "- overview_anomalies_today(customer=..., per_dim_limit=...) for today's buckets.\n"
            "- query_anomalies/query_table is the fallback; when writing SQL use the {{MLA}} macro for the table name.\n\n"
            "Data guidance:\n"
            "- Column names: sales_date (INT YYYYMMDD), customer, cp (competitive position), any_anomaly, impact_score, etc. There is no column named competitive_position or anomaly_date—use cp and sales_date instead.\n"
            "- Always include LIMIT clauses (tools enforce sensible defaults).\n"
            "- Keep answers concise with bullet points ordered by importance and note which tool produced the insight.\n"
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
