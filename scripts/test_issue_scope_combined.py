#!/usr/bin/env python3
"""
E2E test: call the Provider Combined Audit 'issue_scope_combined' tool
to aggregate across multiple dimensions with a single SQL GROUP BY.
"""

import asyncio
import json
from pathlib import Path

from agents.mcp import MCPServerStdio


async def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    wrapper = repo_root / "ds-mcp" / "scripts" / "run_mcp_server.sh"
    if not wrapper.exists():
        raise SystemExit(f"Wrapper not found: {wrapper}")

    async with MCPServerStdio(
            params={"command": "bash", "args": [str(wrapper), "provider"]},
        cache_tools_list=True,
        client_session_timeout_seconds=180.0,
        name="Provider Combined Audit (test)",
    ) as server:
        result = await server.call_tool(
            "issue_scope_combined",
            {
                "provider": "QL2",
                "site": "QF",
                "dims": ["obs_hour", "pos", "triptype", "los"],
                "lookback_days": 7,
                "limit": 40,
            },
        )

        content = None
        if getattr(result, "structured_content", None):
            content = result.structured_content
        else:
            for part in result.content or []:
                if getattr(part, "type", None) == "text":
                    content = getattr(part, "text", None)
                    break
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                pass
        print(json.dumps({"tool": "issue_scope_combined", "result": content}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
