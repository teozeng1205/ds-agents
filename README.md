ds-agents

- What: Minimal chat entrypoint for Provider and Market Anomalies agents. Uses `ds-mcp` servers over stdio.

- Quick Start
  - python -m venv .venv && source .venv/bin/activate
  - pip install -U openai-agents
  - pip install -e ds-threevictors -r ds-mcp/requirements.txt -e ds-mcp
  - Create repo `env.sh` with `AWS_PROFILE`, `AWS_DEFAULT_REGION`, `OPENAI_API_KEY`

- Run
  - Provider: `python ds-agents/chat.py --agent provider`
  - Anomalies: `python ds-agents/chat.py --agent anomalies`

- Docker
  - Build: `docker compose build`
  - Run: `OPENAI_API_KEY=sk-... docker compose run --rm chat-provider` (or `chat-anomalies`)
  - The container mounts host `~/.aws` and repo `env.sh`
