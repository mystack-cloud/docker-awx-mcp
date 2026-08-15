# docker-awx-mcp

[![Build and Publish](https://github.com/mystack-cloud/docker-awx-mcp/actions/workflows/build-and-publish.yml/badge.svg)](https://github.com/mystack-cloud/docker-awx-mcp/actions/workflows/build-and-publish.yml) [![Release](https://img.shields.io/github/v/release/mystack-cloud/docker-awx-mcp)](https://github.com/mystack-cloud/docker-awx-mcp/releases/latest)

Docker image wrapping [`awx-mcp-server`](https://github.com/SurgeX-Labs/awx-mcp-server) for inspecting and operating AWX / Ansible Automation Platform from MCP clients (Cursor, Claude, etc.).

Published to **GHCR**: `ghcr.io/mystack-cloud/docker-awx-mcp`

## Modes

| `MODE` | Purpose | Entrypoint |
|--------|---------|------------|
| `stdio` (default) | Cursor / Claude local MCP over stdin/stdout | `python -m awx_mcp_server` |
| `http` | Remote HTTP/SSE server | `awx-mcp-server start` |

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `AWX_BASE_URL` | Yes | AWX/AAP base URL (e.g. `https://automation-orchestrator-test1.mystack.cloud`) |
| `AWX_USERNAME` | Yes\* | Username (`mystack-delivery-agent` auditor) |
| `AWX_PASSWORD` | Yes\* | Password |
| `AWX_TOKEN` | Yes\* | OAuth/token alternative to username/password |
| `AWX_PLATFORM` | No | `awx` (default), `aap`, or `tower` |
| `AWX_VERIFY_SSL` | No | Default `true` |
| `MODE` | No | `stdio` or `http` |
| `AWX_MCP_HOST` / `AWX_MCP_PORT` | No | HTTP bind (default `0.0.0.0:8000`) |

\* Provide either token **or** username+password.

`AWX_URL` is accepted as an alias for `AWX_BASE_URL`.

## Cursor MCP (stdio via Docker)

```json
{
  "mcpServers": {
    "awx": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWX_BASE_URL",
        "-e", "AWX_USERNAME",
        "-e", "AWX_PASSWORD",
        "-e", "AWX_PLATFORM=awx",
        "ghcr.io/mystack-cloud/docker-awx-mcp:latest"
      ],
      "env": {
        "AWX_BASE_URL": "https://automation-orchestrator-test1.mystack.cloud",
        "AWX_USERNAME": "mystack-delivery-agent"
      },
      "envFile": "${workspaceFolder}/.env"
    }
  }
}
```

Put `AWX_PASSWORD=…` in the project `.env` (gitignored). Reload MCP after changing config.

## Local build

```bash
cp .env.example .env   # set AWX_PASSWORD
docker build -t docker-awx-mcp:local .
docker run --rm -i \
  --env-file .env \
  -e MODE=stdio \
  docker-awx-mcp:local --help
```

HTTP smoke:

```bash
docker compose up --build -d
curl -sS http://127.0.0.1:8000/health || true
```

## CI

GitHub Actions (`.github/workflows/build-and-publish.yml`) builds multi-arch (`linux/amd64`, `linux/arm64`) and pushes to GHCR on `main` and `v*` tags. PRs build without push. Pushing a `v*` tag also creates a [GitHub Release](https://github.com/mystack-cloud/docker-awx-mcp/releases) with generated notes.

Optional repo variable `AWX_MCP_VERSION` pins the PyPI package version (default `1.2.0`).

## Image tags

- `latest` — default branch
- `main` — branch builds
- `vX.Y.Z` / `X.Y.Z` / `X.Y` / `X` — semver tags (also creates a GitHub Release)
