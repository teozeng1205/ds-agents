from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence

from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStdio, create_static_tool_filter


class BaseMCPAgent:
    """Shared scaffolding for every DS MCP agent."""

    name: str = "MCP Agent"
    instructions: str = "Use configured tools to answer the user concisely."
    base_tools: Sequence[str] = ("describe_table", "get_table_schema", "read_table_head", "query_table")
    allowed_tools: Sequence[str] = ()
    client_session_timeout_seconds: float = 180.0

    def __init__(self, name: str | None = None, instructions: str | None = None) -> None:
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

    def create_mcp_server(self, tables: Sequence[str] | None = None) -> MCPServerStdio:
        script = str(self.get_wrapper_script())
        if not os.path.exists(script):
            raise RuntimeError(f"Wrapper script not found: {script}")
        table_args = list(tables or [])
        if not table_args:
            server_kind = getattr(self, "server_kind", None)
            if server_kind:
                table_args = [server_kind]
        params = {
            "command": "bash",
            "args": [script, *table_args],
            "env": {"PYTHON": sys.executable},
        }
        return MCPServerStdio(
            name=self.get_server_name(),
            params=params,
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
        names: dict[str, None] = {tool: None for tool in self.base_tools}
        for tool in self.allowed_tools:
            names.setdefault(tool, None)
        return list(names.keys())
