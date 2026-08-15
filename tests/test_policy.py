#!/usr/bin/env python3
"""Unit tests for restricted MCP policy matching (no AWX needed)."""

import tempfile
import unittest
from pathlib import Path

from restricted.policy import default_policy, load_policy


class PolicyTests(unittest.TestCase):
    def test_default_allows_reads_and_project_update(self):
        p = default_policy()
        self.assertTrue(p.is_tool_allowed("awx_jobs_list"))
        self.assertTrue(p.is_tool_allowed("awx_project_update"))
        self.assertTrue(p.is_tool_allowed("env_list"))
        self.assertFalse(p.is_tool_allowed("awx_job_launch"))
        self.assertFalse(p.is_tool_allowed("awx_project_delete"))

    def test_explicit_allowlist(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(
                "require_api_key: true\n"
                "allowed_tools:\n"
                "  - awx_project_update\n"
                "  - awx_projects_list\n"
            )
            path = f.name
        p = load_policy(path)
        self.assertTrue(p.is_tool_allowed("awx_project_update"))
        self.assertTrue(p.is_tool_allowed("awx_projects_list"))
        self.assertFalse(p.is_tool_allowed("awx_jobs_list"))

    def test_denied_tools_win(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(
                "allowed_tool_patterns: ['awx_*']\n"
                "denied_tools: ['awx_job_launch']\n"
            )
            path = f.name
        p = load_policy(path)
        self.assertFalse(p.is_tool_allowed("awx_job_launch"))
        self.assertTrue(p.is_tool_allowed("awx_jobs_list"))

    def test_filter_tool_list(self):
        p = default_policy()
        tools = [
            {"name": "awx_jobs_list"},
            {"name": "awx_job_launch"},
            {"name": "awx_project_update"},
        ]
        filtered = p.filter_tool_list(tools)
        names = [t["name"] for t in filtered]
        self.assertEqual(names, ["awx_jobs_list", "awx_project_update"])


if __name__ == "__main__":
    unittest.main()
