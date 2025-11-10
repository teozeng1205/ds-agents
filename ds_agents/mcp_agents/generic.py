from __future__ import annotations

from pathlib import Path

from .base import BaseMCPAgent


class GenericDatabaseMCPAgent(BaseMCPAgent):
    name = "Database Explorer (stdio)"

    def __init__(self) -> None:
        instructions = (
            "You are a database exploration agent.\n"
            "1. Start with describe_table() and get_table_partitions() to understand key columns and partition metadata.\n"
            "2. Use get_table_schema() before referencing new columns.\n"
            "3. Use read_table_head(limit=...) for quick previews.\n"
            "4. When invoking query_table(), write SELECT/WITH statements only, keep LIMIT clauses, and include partition filters.\n"
            "Never modify data and cite which tool produced each insight."
        )
        super().__init__(name=self.name, instructions=instructions)

    def get_wrapper_script(self) -> Path:
        return Path(__file__).resolve().parents[3] / "ds-mcp" / "scripts" / "run_mcp_server.sh"
