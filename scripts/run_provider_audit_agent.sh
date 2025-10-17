#!/usr/bin/env bash
set -euo pipefail

# Run the Provider Audit Agent with correct env, venv and PYTHONPATH.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR/../.."

# Load OPENAI_API_KEY from user shell if present
if [ -f "$HOME/.zshrc" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.zshrc" || true
fi

# Ensure our root venv exists
VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then
  echo "Error: root .venv not found at $ROOT_DIR/.venv. Create one and install deps." >&2
  echo "Hint: python3 -m venv .venv && source .venv/bin/activate && (cd openai-agents-python && pip install -e .) && (cd ds-mcp && pip install -e .)" >&2
  exit 1
fi

# Wire Agents SDK + ds-mcp src on sys.path
export PYTHONPATH="$ROOT_DIR/openai-agents-python/src:$ROOT_DIR/ds-mcp/src:$PYTHONPATH"

exec "$VENV_PY" "$ROOT_DIR/ds-agents/agents/provider_audit_agent.py" "$@"

