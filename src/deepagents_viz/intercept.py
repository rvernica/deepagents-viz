from __future__ import annotations

import inspect
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


def _make_recorder(sig):
    """Build a create_deep_agent stand-in that records its call as a kwargs dict."""

    def _record(*args, **kwargs):
        captured = dict(kwargs)
        # Normalize positional args to their parameter names so a call like
        # create_deep_agent(model, tools) is captured as fully as a kwargs call.
        if sig is not None and args:
            try:
                bound = sig.bind_partial(*args)
                for pname, pval in bound.arguments.items():
                    param = sig.parameters.get(pname)
                    if param is not None and param.kind == inspect.Parameter.VAR_POSITIONAL:
                        continue
                    captured.setdefault(pname, pval)
            except TypeError:
                pass
        CAPTURED.append(captured)
        return MagicMock()

    return _record


def install_create_deep_agent_patch() -> None:
    try:
        import deepagents
    except ImportError:
        return
    try:
        sig = inspect.signature(deepagents.create_deep_agent)
    except (TypeError, ValueError):
        sig = None
    deepagents.create_deep_agent = _make_recorder(sig)


def _patch_mcp_class(cls) -> None:
    """Patch an MCP client class so tool discovery is offline (no network)."""
    original_init = cls.__init__

    def patched_init(self, connections=None, *args, **kwargs):
        self._captured_servers = list((connections or {}).keys())
        # The real __init__ may validate or connect; we only need the server
        # names, so any failure here is intentionally swallowed to stay offline.
        try:
            original_init(self, connections, *args, **kwargs)
        except Exception:
            pass

    async def patched_get_tools(self, *args, **kwargs):
        servers = getattr(self, "_captured_servers", [])
        return [MCPPlaceholder(name=s, mcp_server=s) for s in servers]

    cls.__init__ = patched_init
    cls.get_tools = patched_get_tools


def install_mcp_stub() -> None:
    try:
        from langchain_mcp_adapters import client as mcp_client
    except ImportError:
        return
    _patch_mcp_class(mcp_client.MultiServerMCPClient)
