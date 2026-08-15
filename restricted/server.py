"""Restricted HTTP entry for AWX MCP: API key + config-driven tool policy."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from restricted.policy import McpPolicy, is_awx_override_header, load_policy


def _seed_api_key() -> Optional[str]:
    """Load static client API key into upstream API_KEYS store."""
    import awx_mcp_server.http_server as http_server

    api_key = os.environ.get("AWX_MCP_API_KEY", "").strip()
    if not api_key:
        return None
    http_server.API_KEYS[api_key] = {
        "name": "static",
        "tenant_id": os.environ.get("AWX_MCP_TENANT_ID", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
    }
    return api_key


def _jsonrpc_error(msg_id: Any, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        },
    )


def _filter_tools_list_result(payload: dict[str, Any], policy: McpPolicy) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload
    tools = result.get("tools")
    if not isinstance(tools, list):
        return payload
    filtered = policy.filter_tool_list(tools)
    new_payload = dict(payload)
    new_result = dict(result)
    new_result["tools"] = filtered
    new_payload["result"] = new_result
    return new_payload


async def _read_json_body(request: Request) -> tuple[bytes, Optional[dict[str, Any]]]:
    body = await request.body()
    if not body:
        return body, None
    try:
        return body, json.loads(body.decode("utf-8"))
    except Exception:
        return body, None


def install_restricted_middleware(app: Any, policy: McpPolicy, static_api_key: Optional[str]) -> None:
    """Wrap FastAPI app with API-key enforcement and tool policy filtering."""

    allowed_paths_exact = {"/", "/health", "/docs", "/redoc", "/openapi.json", "/prometheus-metrics"}
    allowed_path_prefixes = ("/mcp",)

    @app.middleware("http")
    async def restricted_policy_middleware(request: Request, call_next: Callable):
        path = request.url.path

        # Strip client AWX credential override headers when configured.
        if policy.deny_awx_client_overrides:
            headers = [
                (k, v)
                for k, v in request.scope.get("headers", [])
                if not is_awx_override_header(k.decode("latin-1"))
            ]
            request.scope["headers"] = headers

        # Require API key for everything except public health/docs/metrics.
        public = path in allowed_paths_exact or path.startswith("/docs") or path.startswith("/redoc")
        if policy.require_api_key and not public:
            provided = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
            if not provided or (static_api_key and provided != static_api_key):
                # Also accept any key seeded into API_KEYS (static is the only one we seed).
                import awx_mcp_server.http_server as http_server

                if not provided or provided not in http_server.API_KEYS:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or missing X-API-Key"},
                    )

        # Block non-MCP write/admin HTTP surfaces in restricted mode.
        if not public and not any(path.startswith(p) for p in allowed_path_prefixes):
            if path.startswith("/api/") or path == "/messages":
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Endpoint disabled in restricted MCP mode"},
                )

        if path == "/mcp" and request.method == "POST":
            body, message = await _read_json_body(request)

            async def receive() -> dict[str, Any]:
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(request.scope, receive)

            if isinstance(message, dict) and message.get("method") == "tools/call":
                tool_name = (message.get("params") or {}).get("name")
                if not tool_name or not policy.is_tool_allowed(str(tool_name)):
                    return _jsonrpc_error(
                        message.get("id"),
                        -32601,
                        f"Tool '{tool_name}' is not allowed by MCP policy",
                    )

            response = await call_next(request)

            if isinstance(message, dict) and message.get("method") == "tools/list":
                # Filter tools/list result body.
                resp_body = b""
                async for chunk in response.body_iterator:
                    resp_body += chunk
                try:
                    payload = json.loads(resp_body.decode("utf-8"))
                    if isinstance(payload, dict) and "result" in payload:
                        payload = _filter_tools_list_result(payload, policy)
                        resp_body = json.dumps(payload).encode("utf-8")
                except Exception:
                    pass
                headers = dict(response.headers)
                headers.pop("content-length", None)
                return Response(
                    content=resp_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type,
                )

            return response

        return await call_next(request)


async def start_restricted_http_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False,
) -> None:
    from awx_mcp_server.http_server import create_app, start_http_server  # noqa: F401
    from awx_mcp_server.utils import configure_logging, get_logger
    import uvicorn

    configure_logging(debug=debug)
    logger = get_logger(__name__)

    policy_file = os.environ.get("AWX_MCP_POLICY_FILE", "/etc/awx-mcp/policy.yaml")
    # Fall back to image default if mount missing
    if not os.path.isfile(policy_file):
        bundled = os.path.join(os.path.dirname(__file__), "..", "policy.default.yaml")
        bundled = os.path.abspath(bundled)
        policy_file = bundled if os.path.isfile(bundled) else None

    policy = load_policy(policy_file)
    static_key = _seed_api_key()
    if policy.require_api_key and not static_key:
        raise SystemExit(
            "AWX_MCP_API_KEY is required when policy.require_api_key is true"
        )

    try:
        from awx_mcp_server.mcp_server import create_mcp_server

        mcp_server = create_mcp_server()
    except ImportError:
        from mcp.server import Server

        mcp_server = Server("awx-mcp-server")

    app = create_app(mcp_server)
    install_restricted_middleware(app, policy, static_key)

    logger.info(
        "starting_restricted_http_server",
        host=host,
        port=port,
        policy_file=policy_file,
        require_api_key=policy.require_api_key,
    )

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    host = os.environ.get("AWX_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("AWX_MCP_PORT", "8000"))
    debug = os.environ.get("LOG_LEVEL", "").lower() == "debug"
    asyncio.run(start_restricted_http_server(host=host, port=port, debug=debug))


if __name__ == "__main__":
    main()
