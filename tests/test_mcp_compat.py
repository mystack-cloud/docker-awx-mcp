#!/usr/bin/env python3
"""Unit tests for MCP client compatibility helpers."""

import unittest

from restricted.mcp_compat import (
    empty_resources_list_response,
    sanitize_tool,
    sanitize_tools_list_result,
)


class McpCompatTests(unittest.TestCase):
    def test_sanitize_tool_drops_null_optional_fields(self):
        tool = {
            "name": "awx_system_info",
            "description": "Get AWX system info",
            "inputSchema": {"type": "object"},
            "title": None,
            "icons": None,
            "outputSchema": None,
            "annotations": None,
            "execution": None,
            "meta": None,
        }
        sanitized = sanitize_tool(tool)
        self.assertEqual(
            sanitized,
            {
                "name": "awx_system_info",
                "description": "Get AWX system info",
                "inputSchema": {"type": "object"},
            },
        )

    def test_sanitize_tools_list_result(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "env_list",
                        "title": None,
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        }
        sanitized = sanitize_tools_list_result(payload)
        self.assertEqual(
            sanitized["result"]["tools"],
            [{"name": "env_list", "inputSchema": {"type": "object"}}],
        )

    def test_empty_resources_list_response(self):
        self.assertEqual(
            empty_resources_list_response(7),
            {"jsonrpc": "2.0", "id": 7, "result": {"resources": []}},
        )


if __name__ == "__main__":
    unittest.main()
