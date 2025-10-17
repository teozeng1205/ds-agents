#!/usr/bin/env bash
set -euo pipefail

# Wrapper to launch the Market Anomalies MCP server over stdio
# using env.sh (new) instead of legacy .env.sh.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR/../.."
DS_MCP_DIR="$ROOT_DIR/ds-mcp"

# Source env.sh (required)
ENV_FILE="$ROOT_DIR/env.sh"
if [ ! -f "$ENV_FILE" ] && [ -f "$ROOT_DIR/../env.sh" ]; then
  ENV_FILE="$ROOT_DIR/../env.sh"
fi
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
else
  echo "Error: env.sh not found at $ROOT_DIR/env.sh or parent" >&2
  exit 1
fi

# Reuse shared AWS SSO setup (serialized login)
# shellcheck disable=SC1090
source "$DS_MCP_DIR/scripts/common_aws_setup.sh"

# Use repo root .venv
VENV_PY="$ROOT_DIR/.venv/bin/python3"
if [ ! -x "$VENV_PY" ]; then
  echo "Error: root .venv not found at $ROOT_DIR/.venv. Create one and install deps." >&2
  echo "Hint: python3 -m venv .venv && source .venv/bin/activate && (cd openai-agents-python && pip install -e .) && (cd ds-mcp && pip install -e .) && (cd ds-threevictors && pip install -e .)" >&2
  exit 1
fi

# Ensure ds-mcp sources are importable (servers also add repo root for threevictors)
export PYTHONPATH="$DS_MCP_DIR/src:$ROOT_DIR:${PYTHONPATH:-}"

exec "$VENV_PY" "$DS_MCP_DIR/src/ds_mcp/servers/market_anomalies_server.py"
