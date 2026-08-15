"""Policy loading and tool allow/deny checks for restricted AWX MCP HTTP mode."""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


DEFAULT_ALLOWED_TOOL_PATTERNS = [
    "env_*",
    "awx_system_info",
    "awx_organizations_*",
    "awx_organization_get",
    "awx_credentials_list",
    "awx_credential_types_list",
    "awx_templates_list",
    "awx_projects_list",
    "awx_inventories_list",
    "awx_inventory_groups_list",
    "awx_inventory_hosts_list",
    "awx_jobs_list",
    "awx_job_get",
    "awx_job_stdout",
    "awx_job_events",
    "awx_job_failure_summary",
]

DEFAULT_EXTRA_ALLOWED_TOOLS = [
    "awx_project_update",
]


@dataclass
class McpPolicy:
    require_api_key: bool = True
    deny_awx_client_overrides: bool = True
    allowed_tools: list[str] = field(default_factory=list)
    allowed_tool_patterns: list[str] = field(default_factory=list)
    extra_allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)

    def is_tool_allowed(self, name: str) -> bool:
        if name in self.denied_tools:
            return False
        if self.allowed_tools:
            return name in self.allowed_tools or name in self.extra_allowed_tools
        if name in self.extra_allowed_tools:
            return True
        patterns = self.allowed_tool_patterns or DEFAULT_ALLOWED_TOOL_PATTERNS
        return any(fnmatch.fnmatch(name, pat) for pat in patterns)

    def filter_tool_list(self, tools: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return [t for t in tools if self.is_tool_allowed(str(t.get("name", "")))]


def default_policy() -> McpPolicy:
    return McpPolicy(
        require_api_key=True,
        deny_awx_client_overrides=True,
        allowed_tool_patterns=list(DEFAULT_ALLOWED_TOOL_PATTERNS),
        extra_allowed_tools=list(DEFAULT_EXTRA_ALLOWED_TOOLS),
    )


def load_policy(path: Optional[str | Path] = None) -> McpPolicy:
    if path is None:
        return default_policy()
    policy_path = Path(path)
    if not policy_path.is_file():
        raise FileNotFoundError(f"MCP policy file not found: {policy_path}")

    raw_text = policy_path.read_text(encoding="utf-8")
    data = _parse_policy_text(raw_text, policy_path)
    if not isinstance(data, dict):
        raise ValueError(f"MCP policy root must be a mapping: {policy_path}")

    base = default_policy()
    return McpPolicy(
        require_api_key=bool(data.get("require_api_key", base.require_api_key)),
        deny_awx_client_overrides=bool(
            data.get("deny_awx_client_overrides", base.deny_awx_client_overrides)
        ),
        allowed_tools=list(data.get("allowed_tools") or []),
        allowed_tool_patterns=list(
            data.get("allowed_tool_patterns") or base.allowed_tool_patterns
        ),
        extra_allowed_tools=list(
            data.get("extra_allowed_tools")
            if "extra_allowed_tools" in data
            else base.extra_allowed_tools
        ),
        denied_tools=list(data.get("denied_tools") or []),
    )


def _parse_policy_text(raw_text: str, path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML MCP policy files")
        return yaml.safe_load(raw_text)
    if suffix == ".json":
        return json.loads(raw_text)
    # Try YAML first, then JSON
    if yaml is not None:
        try:
            return yaml.safe_load(raw_text)
        except Exception:
            pass
    return json.loads(raw_text)


_AWX_OVERRIDE_HEADER = re.compile(r"^x-awx-", re.IGNORECASE)


def is_awx_override_header(name: str) -> bool:
    return bool(_AWX_OVERRIDE_HEADER.match(name))
