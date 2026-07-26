"""Load external MCP tools for the Zhiban agent.

The agent treats MCP tools as optional. If the config file is absent, a server is
unavailable, or the adapter package is not installed, the normal local tools
continue to work.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "mcp_servers.json"
ENV_CONFIG_PATH = "ZHIBAN_MCP_CONFIG"
ENV_ENABLED = "ZHIBAN_MCP_ENABLED"
ENV_TIMEOUT = "ZHIBAN_MCP_LOAD_TIMEOUT_SEC"
TOOL_PREFIX = "mcp_"


def _mcp_enabled() -> bool:
    return os.getenv(ENV_ENABLED, "true").strip().lower() not in {"0", "false", "no", "off"}


def _load_timeout() -> float:
    try:
        return max(1.0, float(os.getenv(ENV_TIMEOUT, "8")))
    except (TypeError, ValueError):
        return 8.0


def _config_path() -> Path:
    value = os.getenv(ENV_CONFIG_PATH)
    return Path(value).expanduser() if value else DEFAULT_CONFIG_PATH


def _expand_env(value: Any) -> Any:
    """Expand ${VAR} placeholders in config values."""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
        return pattern.sub(lambda match: os.getenv(match.group(1), ""), value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def _normalize_servers(config: dict[str, Any]) -> dict[str, Any]:
    servers = config.get("servers", config)
    if not isinstance(servers, dict):
        return {}

    normalized: dict[str, Any] = {}
    for name, server in servers.items():
        if not isinstance(server, dict) or server.get("enabled", True) is False:
            continue

        clean = {key: value for key, value in server.items() if key != "enabled"}
        transport = clean.get("transport")
        if transport == "http":
            clean["transport"] = "streamable_http"
        elif transport == "sse":
            clean["transport"] = "sse"
        elif not transport:
            clean["transport"] = "streamable_http" if clean.get("url") else "stdio"

        clean = _expand_env(clean)
        if clean["transport"] in {"streamable_http", "sse"} and not clean.get("url"):
            logger.warning("Skip MCP server %s: missing url", name)
            continue
        if clean["transport"] == "stdio" and not clean.get("command"):
            logger.warning("Skip MCP server %s: missing command", name)
            continue

        normalized[str(name)] = clean
    return normalized


def _prefix_tool_name(tool: Any) -> None:
    raw_name = getattr(tool, "name", "")
    if raw_name and not raw_name.startswith(TOOL_PREFIX):
        tool.name = f"{TOOL_PREFIX}{raw_name}"


async def load_external_mcp_tools() -> list[Any]:
    """Return LangChain-compatible tools exposed by configured MCP servers."""
    if not _mcp_enabled():
        return []

    path = _config_path()
    if not path.exists():
        logger.info("MCP config not found, skip external MCP tools: %s", path)
        return []

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        servers = _normalize_servers(config)
    except Exception:
        logger.exception("Failed to read MCP config: %s", path)
        return []

    if not servers:
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except Exception:
        logger.warning("langchain-mcp-adapters is not installed; skip external MCP tools")
        return []

    all_tools: list[Any] = []
    timeout = _load_timeout()
    for name, server in servers.items():
        try:
            client = MultiServerMCPClient({name: server})
            tools = await asyncio.wait_for(client.get_tools(), timeout=timeout)
            for tool in tools:
                _prefix_tool_name(tool)
            all_tools.extend(tools)
            logger.info("Loaded %d MCP tools from %s", len(tools), name)
        except Exception:
            logger.exception("Failed to load MCP server %s from %s", name, path)

    logger.info("Loaded %d MCP tools total from %s", len(all_tools), path)
    return all_tools