from __future__ import annotations

from pathlib import Path

from .base import BaseMCPAgent


class GenericDatabaseMCPAgent(BaseMCPAgent):
    name = "Database Explorer (stdio)"

    def __init__(self) -> None:
        instructions = (
            "You are a database exploration and monitoring agent.\n\n"
            "GENERAL DATABASE EXPLORATION:\n"
            "1. Start with describe_table() and get_table_partitions() to understand key columns and partition metadata.\n"
            "2. Use get_table_schema() before referencing new columns.\n"
            "3. Use read_table_head(limit=...) for quick previews.\n"
            "4. When invoking query_table(), write SELECT/WITH statements only, keep LIMIT clauses, and include partition filters.\n\n"
            "PROVIDER MONITORING TOOLS:\n"
            "5. Use get_top_site_issues(target_date) to identify top site issues for a specific date and compare with last week/month.\n"
            "   - Accepts date in YYYYMMDD format (e.g., '20251109')\n"
            "   - Returns issue_sources, issue_reasons, and counts with trend analysis\n"
            "6. Use analyze_issue_scope(providercode, sitecode, target_date, lookback_days) to analyze issue dimensions.\n"
            "   - Breaks down issues by POS, triptype, LOS, cabin, O&D, depart dates, day of week, observation hour\n"
            "   - Example: analyze_issue_scope('QL2', 'QF', '20251109', 7) for QL2/QF issues over last 7 days\n\n"
            "Never modify data and cite which tool produced each insight."
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "ds-mcp" / "scripts" / "run_mcp_server.sh"
