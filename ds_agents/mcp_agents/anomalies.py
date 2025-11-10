from __future__ import annotations

from pathlib import Path

from .base import BaseMCPAgent


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
            "Workflow:\n"
            "1. Start with describe_table()/get_table_schema() to refresh column context.\n"
            "2. Prefer built-in tools (get_available_customers, overview_anomalies_today) before issuing custom SQL via query_table().\n"
            "3. When writing SQL, use provided macros ({{MLA}}) and include sales_date filters with LIMITs.\n"
            "4. Report insights as concise bullets referencing the tool used."
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "ds-mcp" / "scripts" / "run_mcp_server.sh"
