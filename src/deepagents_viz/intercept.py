from __future__ import annotations

import os
from unittest.mock import MagicMock

CAPTURED: list[dict] = []

_DUMMY_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
)


def reset() -> None:
    CAPTURED.clear()


def set_dummy_env() -> None:
    for key in _DUMMY_KEYS:
        os.environ.setdefault(key, "dummy")


class MCPPlaceholder:
    """Stand-in for an MCP tool; carries only its originating server name."""

    def __init__(self, name: str, mcp_server: str):
        self.name = name
        self.mcp_server = mcp_server


def _record(*_args, **kwargs):
    CAPTURED.append(kwargs)
    return MagicMock()


def install_create_deep_agent_patch() -> None:
    try:
        import deepagents
    except Exception:
        return
    deepagents.create_deep_agent = _record


def install_mcp_stub() -> None:
    try:
        from langchain_mcp_adapters import client as mcp_client
    except Exception:
        return

    cls = mcp_client.MultiServerMCPClient
    original_init = cls.__init__

    def patched_init(self, connections=None, *args, **kwargs):
        self._captured_servers = list((connections or {}).keys())
        try:
            original_init(self, connections, *args, **kwargs)
        except Exception:
            pass

    async def patched_get_tools(self, *args, **kwargs):
        servers = getattr(self, "_captured_servers", [])
        return [MCPPlaceholder(name=s, mcp_server=s) for s in servers]

    cls.__init__ = patched_init
    cls.get_tools = patched_get_tools
