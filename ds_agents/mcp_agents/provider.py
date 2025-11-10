from __future__ import annotations

from pathlib import Path

from .base import BaseMCPAgent


class ProviderAuditMCPAgent(BaseMCPAgent):
    name = "Provider Combined Audit (stdio)"
    server_kind = "provider"
    allowed_tools = (
        "query_audit",
        "top_site_issues",
        "top_site_issues_flex",
        "issue_scope_combined",
        "issue_scope_combined_all",
        "issue_scope_combined_flex",
    )

    def __init__(self) -> None:
        instructions = (
            "You are the Provider Combined Audit agent.\n"
            "Workflow:\n"
            "1. Parse each request for provider, site, lookback window, and requested dimensions. Normalise provider/site codes to uppercase strings.\n"
            "2. Prefer the built-in MCP tools (issue_scope*, top_site_issues*) before writing SQL with query_table().\n"
            "3. When you must write SQL, rely on macros ({{PCA}}, {{ISSUE_TYPE}}, {{EVENT_TS:alias}}) and always filter on sales_date with a LIMIT clause.\n"
            "4. Parse JSON tool responses, cite the tool name, and keep answers concise."
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "ds-mcp" / "scripts" / "run_mcp_server.sh"
