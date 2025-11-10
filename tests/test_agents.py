from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ds_agents.mcp_agents import (
    GenericDatabaseMCPAgent,
    MarketAnomaliesMCPAgent,
    ProviderAuditMCPAgent,
)


def test_provider_agent_allowed_tools():
    agent = ProviderAuditMCPAgent()
    names = set(agent.allowed_tool_names())
    assert "query_audit" in names
    assert "describe_table" in names


def test_anomalies_agent_tools():
    agent = MarketAnomaliesMCPAgent()
    names = set(agent.allowed_tool_names())
    assert "overview_anomalies_today" in names
    assert "read_table_head" in names


def test_generic_agent_instructions_reference_discovery():
    agent = GenericDatabaseMCPAgent()
    assert "describe_table" in agent.instructions
