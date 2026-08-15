#!/usr/bin/env sh
set -eu

# MODE:
#   stdio (default) — MCP over stdin/stdout for Cursor / Claude
#   http            — remote HTTP/SSE server (awx-mcp-server start)
MODE="${MODE:-stdio}"
HOST="${AWX_MCP_HOST:-0.0.0.0}"
PORT="${AWX_MCP_PORT:-8000}"

# Prefer AWX_BASE_URL (package stdio entry). Accept AWX_URL as alias.
if [ -z "${AWX_BASE_URL:-}" ] && [ -n "${AWX_URL:-}" ]; then
  export AWX_BASE_URL="$AWX_URL"
fi

case "$MODE" in
  stdio|mcp)
    if [ "$#" -gt 0 ]; then
      case "$1" in
        -*)
          exec python -m awx_mcp_server "$@"
          ;;
        *)
          exec "$@"
          ;;
      esac
    fi
    exec python -m awx_mcp_server
    ;;
  http|server|start)
    exec awx-mcp-server start --host "$HOST" --port "$PORT"
    ;;
  *)
    echo "Unknown MODE='$MODE' (expected: stdio|http)" >&2
    exit 1
    ;;
esac
