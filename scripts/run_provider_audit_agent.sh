#!/usr/bin/env bash
set -euo pipefail

# Run the Provider Audit Agent with correct env, venv and PYTHONPATH.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR/../.."

# Load OPENAI_API_KEY from repo env.sh or user shell
if [ -f "$ROOT_DIR/env.sh" ]; then
  # shellcheck disable=SC1090
  source "$ROOT_DIR/env.sh" || true
elif [ -f "$HOME/.zshrc" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.zshrc" || true
fi

# Ensure our root venv exists
VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then
  echo "Error: root .venv not found at $ROOT_DIR/.venv. Create one and install deps." >&2
  echo "Hint: python3 -m venv .venv && source .venv/bin/activate && pip install openai-agents && (cd ds-mcp && pip install -e .)" >&2
  exit 1
fi

# Use the installed OpenAI Agents SDK (pip install openai-agents). No PYTHONPATH override needed.
# ds-mcp MCP server script handles its own PYTHONPATH internally.

exec "$VENV_PY" "$ROOT_DIR/ds-agents/agents/provider_audit_agent.py" "$@"
