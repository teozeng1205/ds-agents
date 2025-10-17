#!/usr/bin/env python3
"""
Call the Provider Combined Audit 'overview_site_issues_today' tool directly via MCP stdio,
without requiring an LLM API key. Useful for end-to-end validation of the tool.
"""

import asyncio
import json
from pathlib import Path

from agents.mcp import MCPServerStdio


async def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    wrapper = repo_root / "ds-agents" / "scripts" / "run_mcp_provider_audit_stdio.sh"
    if not wrapper.exists():
        raise SystemExit(f"Wrapper not found: {wrapper}")

    async with MCPServerStdio(
        params={"command": "bash", "args": [str(wrapper)]},
        cache_tools_list=True,
        client_session_timeout_seconds=180.0,
        name="Provider Combined Audit (test)",
    ) as server:
        tools = await server.list_tools()
        names = [t.name for t in tools]
        if "overview_site_issues_today" not in names:
            raise SystemExit("overview_site_issues_today tool not found on server")

        result = await server.call_tool("overview_site_issues_today", {"per_dim_limit": 20})
        # Prefer structured content if present; otherwise fall back to content text
        content = None
        if getattr(result, "structured_content", None):
            content = result.structured_content
        else:
            # 'content' is a list of parts (pydantic models); take first text
            for part in result.content or []:
                if getattr(part, "type", None) == "text":
                    content = getattr(part, "text", None)
                    break
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                pass
        print(json.dumps({"tool": "overview_site_issues_today", "result": content}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
