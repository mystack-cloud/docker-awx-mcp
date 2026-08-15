# docker-awx-mcp

[![Build and Publish](https://github.com/mystack-cloud/docker-awx-mcp/actions/workflows/build-and-publish.yml/badge.svg)](https://github.com/mystack-cloud/docker-awx-mcp/actions/workflows/build-and-publish.yml) [![Release](https://img.shields.io/github/v/release/mystack-cloud/docker-awx-mcp?logo=github&label=release&cacheSeconds=3600)](https://github.com/mystack-cloud/docker-awx-mcp/releases/latest)

Docker image wrapping [`awx-mcp-server`](https://github.com/SurgeX-Labs/awx-mcp-server) for inspecting and operating AWX / Ansible Automation Platform from MCP clients (Cursor, Claude, etc.).

Published to **GHCR**: `ghcr.io/mystack-cloud/docker-awx-mcp`

## Modes

| `MODE` | Purpose | Entrypoint |
|--------|---------|------------|
| `stdio` (default) | Cursor / Claude local MCP over stdin/stdout | `python -m awx_mcp_server` |
| `http` | Upstream remote HTTP/SSE (unrestricted tools) | `awx-mcp-server start` |
| `http-restricted` | HTTP + static `X-API-Key` + policy-file tool allowlist | `python -m restricted.server` |

## Restricted HTTP (`MODE=http-restricted`)

Use this for shared / remote MCP. The image loads policy from `AWX_MCP_POLICY_FILE` (default `/etc/awx-mcp/policy.yaml`). Changing allowlists is a ConfigMap/file edit — no image rebuild.

Default policy: AWX **read/inspect** tools + **`awx_project_update`** (SCM sync). Job launch and project Admin tools are denied.

| Variable | Required | Description |
|----------|----------|-------------|
| `AWX_MCP_API_KEY` | Yes\* | Static client key; clients send `X-API-Key` |
| `AWX_MCP_POLICY_FILE` | No | Policy YAML/JSON path (default `/etc/awx-mcp/policy.yaml`) |

\* When `require_api_key: true` in the policy file.

`X-AWX-*` client override headers are stripped when `deny_awx_client_overrides: true` (default). Non-MCP `/api/*` HTTP surfaces are blocked.

Policy schema (see `policy.default.yaml`):

```yaml
require_api_key: true
deny_awx_client_overrides: true
allowed_tool_patterns: [...]   # or explicit allowed_tools: [...]
extra_allowed_tools:
  - awx_project_update
denied_tools: []
```

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `AWX_BASE_URL` | Yes | AWX/AAP base URL (e.g. `https://automation-orchestrator-test1.mystack.cloud`) |
| `AWX_USERNAME` | Yes\* | Username (`mystack-delivery-agent`) |
| `AWX_PASSWORD` | Yes\* | Password |
| `AWX_TOKEN` | Yes\* | OAuth/token alternative to username/password |
| `AWX_PLATFORM` | No | `awx` (default), `aap`, or `tower` |
| `AWX_VERIFY_SSL` | No | Default `true` |
| `MODE` | No | `stdio`, `http`, or `http-restricted` |
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
        "ghcr.io/mystack-cloud/docker-awx-mcp:0.2.0"
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

### Remote restricted HTTP (test1)

```json
{
  "mcpServers": {
    "awx": {
      "url": "https://awx-mcp-test1.mystack.cloud/mcp",
      "headers": {
        "X-API-Key": "${AWX_MCP_API_KEY}"
      }
    }
  }
}
```

> Note: docker-metadata publishes semver tags **without** the leading `v` (`0.2.0`). From tagged builds, the git tag name (`v0.2.0`) is also pushed.

## Local build

```bash
cp .env.example .env   # set AWX_PASSWORD (+ AWX_MCP_API_KEY for restricted)
docker build -t docker-awx-mcp:local .
docker run --rm -i \
  --env-file .env \
  -e MODE=stdio \
  docker-awx-mcp:local --help
```

Restricted HTTP smoke:

```bash
docker compose up --build -d
curl -sS -H "X-API-Key: $AWX_MCP_API_KEY" http://127.0.0.1:8000/health
# tools/list should omit awx_job_launch; tools/call for it should fail policy
```

Policy unit tests (no AWX):

```bash
PYTHONPATH=. python -m unittest tests.test_policy -v
```

## CI

GitHub Actions (`.github/workflows/build-and-publish.yml`) builds multi-arch (`linux/amd64`, `linux/arm64`) and pushes to GHCR on `main` and `v*` tags. PRs build without push. Pushing a `v*` tag also creates a [GitHub Release](https://github.com/mystack-cloud/docker-awx-mcp/releases) with generated notes.

Optional repo variable `AWX_MCP_VERSION` pins the PyPI package version (default `1.2.0`).

## Image tags

- `latest` — default branch
- `main` — branch builds
- `vX.Y.Z` / `X.Y.Z` / `X.Y` / `X` — semver tags (also creates a GitHub Release)
