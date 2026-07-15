from __future__ import annotations

import inspect
import os
from unittest.mock import MagicMock

CAPTURED: list[dict] = []

_original_create_deep_agent = None

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
        index = len(CAPTURED)
        CAPTURED.append(captured)
        result = MagicMock()
        result._deepagents_viz_index = index
        return result

    _record._deepagents_viz_recorder = True
    return _record


def install_create_deep_agent_patch() -> None:
    """Replace deepagents.create_deep_agent with a recorder. Idempotent: a second
    call while already patched is a no-op, so the recorder keeps the signature
    built from the *real* function rather than re-inspecting itself."""
    global _original_create_deep_agent
    try:
        import deepagents
    except ImportError:
        return
    current = deepagents.create_deep_agent
    if getattr(current, "_deepagents_viz_recorder", False):
        return
    _original_create_deep_agent = current
    try:
        sig = inspect.signature(current)
    except (TypeError, ValueError):
        sig = None
    deepagents.create_deep_agent = _make_recorder(sig)


def uninstall_create_deep_agent_patch() -> None:
    """Restore the original deepagents.create_deep_agent if we patched it."""
    global _original_create_deep_agent
    if _original_create_deep_agent is None:
        return
    try:
        import deepagents
    except ImportError:
        _original_create_deep_agent = None
        return
    deepagents.create_deep_agent = _original_create_deep_agent
    _original_create_deep_agent = None


def _patch_mcp_class(cls) -> None:
    """Patch an MCP client class so tool discovery is offline (no network).
    Idempotent, and reversible via _unpatch_mcp_class."""
    if getattr(cls, "_deepagents_viz_patched", False):
        return
    original_init = cls.__init__
    original_get_tools = getattr(cls, "get_tools", None)

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

    cls._deepagents_viz_original = (original_init, original_get_tools)
    cls.__init__ = patched_init
    cls.get_tools = patched_get_tools
    cls._deepagents_viz_patched = True


def _unpatch_mcp_class(cls) -> None:
    """Restore a class previously patched by _patch_mcp_class."""
    saved = getattr(cls, "_deepagents_viz_original", None)
    if saved is None:
        return
    original_init, original_get_tools = saved
    cls.__init__ = original_init
    if original_get_tools is None:
        if "get_tools" in cls.__dict__:
            del cls.get_tools
    else:
        cls.get_tools = original_get_tools
    del cls._deepagents_viz_original
    cls._deepagents_viz_patched = False


def install_mcp_stub() -> None:
    try:
        from langchain_mcp_adapters import client as mcp_client
    except ImportError:
        return
    _patch_mcp_class(mcp_client.MultiServerMCPClient)


def uninstall_mcp_stub() -> None:
    try:
        from langchain_mcp_adapters import client as mcp_client
    except ImportError:
        return
    _unpatch_mcp_class(mcp_client.MultiServerMCPClient)
