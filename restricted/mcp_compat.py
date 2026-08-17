"""MCP response shaping for strict clients (e.g. Cursor)."""

from __future__ import annotations

from typing import Any


def sanitize_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Drop null optional fields from a tools/list entry.

    awx-mcp-server serializes optional MCP tool fields as JSON null. Cursor's
    MCP client rejects those entries instead of treating them as omitted.
    """
    return {key: value for key, value in tool.items() if value is not None}


def sanitize_tools_list_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload
    tools = result.get("tools")
    if not isinstance(tools, list):
        return payload

    new_payload = dict(payload)
    new_result = dict(result)
    new_result["tools"] = [sanitize_tool(tool) for tool in tools if isinstance(tool, dict)]
    new_payload["result"] = new_result
    return new_payload


def empty_resources_list_response(msg_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": {"resources": []},
    }
