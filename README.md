Provider Audit Agent (ds-agents)

Overview
- A small agent that connects to the ds-mcp Provider Combined Audit MCP server and answers:
  1) Top site-related issues for a provider
  2) Scope/concentration across key dimensions (obs hour, POS, OD, cabin, depart periods). 

Prereqs
- OPENAI_API_KEY available in your shell (e.g., ~/.zshrc). The run script will source it.
- AWS creds via ds-mcp’s .env.sh (profile 3VDEV by default). The MCP run script handles SSO.
- Root-level virtualenv: .venv

Run
- Use the helper script which wires PYTHONPATH for the Agents SDK and MCP:
- ds-agents/scripts/run_provider_audit_agent.sh "Your question here"

Examples
- ds-agents/scripts/run_provider_audit_agent.sh "provider code QL2 with site code QF has an increase in site issues recently. What are the top site issues?"
- ds-agents/scripts/run_provider_audit_agent.sh "provider code QL2 with site code QF: What is the scope of the issue (obs hour/POS/OD/cabin/depart periods)?"

Notes
- The agent uses MCP stdio to spawn ds-mcp/scripts/run_provider_combined_audit.sh.
- The agent prefers built-in tools (top_site_issues, issue_scope_breakdown) and can fall back to query_audit with macros for finer filtering (e.g., sitecode).

