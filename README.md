Provider Audit Agent (ds-agents)

Overview
- Agents that connect to ds-mcp MCP servers and answer:
  1) Top site-related issues for a provider (reasons or sources)
  2) Scope across key dimensions using a single SQL (obs hour, POS, triptype, LOS, etc.)

Prereqs
- Create and source a repo-level `.venv` (python -m venv .venv)
- pip install openai-agents and ds-mcp (editable, optional)
- Set up env.sh at the repo root with AWS_PROFILE/region and OPENAI_API_KEY

Run
- Provider: ds-agents/scripts/run_provider_audit_agent.sh "Your question here"
- Anomalies: ds-agents/scripts/run_market_anomalies_agent.sh "Your question here"

Notes
- Agents launch MCP servers via env.sh-first wrappers which serialize AWS SSO login.
- Provider tools: query_audit, get_table_schema, top_site_issues, list_provider_sites, issue_scope_combined, overview_site_issues_today.
- No hidden fallbacks: if a tool is misused (e.g., dims invalid), it returns a clear error message.
