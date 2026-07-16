from __future__ import annotations

from deepagents_viz.model import AgentModel, MiddlewareInfo, ToolInfo


def model_label(model) -> str:
    if model is None:
        return ""
    if isinstance(model, str):
        return model
    for attr in ("model", "model_name"):
        val = getattr(model, attr, None)
        if isinstance(val, str) and val:
            return val
    return type(model).__name__


def tool_info(tool, gated_names: set[str]) -> ToolInfo:
    raw_name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
    gated = str(raw_name) in gated_names if raw_name is not None else False
    server = getattr(tool, "mcp_server", None) or getattr(tool, "_mcp_server", None)
    if server:
        return ToolInfo(name=str(server), kind="mcp", mcp_server=str(server), gated=gated)
    name = raw_name if raw_name is not None else repr(tool)
    return ToolInfo(name=str(name), kind="function", gated=str(name) in gated_names)


def permission_labels(permissions) -> list[str]:
    labels: list[str] = []
    for p in permissions or []:
        mode = getattr(p, "mode", "?")
        ops = ",".join(getattr(p, "operations", []) or [])
        paths = ",".join(getattr(p, "paths", []) or [])
        labels.append(f"{mode} {ops} {paths}".strip())
    return labels


# Tools that each DeepAgents-bundled middleware contributes (introspected from the
# default middleware instances). Skills/Memory register no tools.
# `execute` is deliberately excluded: FilesystemMiddleware registers it unconditionally,
# but it only works with a SandboxBackendProtocol backend and errors at runtime otherwise
# — which we can't tell from the inferred defaults. The six below are always live.
BUILTIN_TOOLS: dict[str, list[str]] = {
    "Planning": ["write_todos"],
    "Filesystem": ["ls", "read_file", "write_file", "edit_file", "glob", "grep"],
    "SubAgent": ["task"],
}


def builtin_tools(middleware: list[MiddlewareInfo]) -> list[ToolInfo]:
    """Built-in tools contributed by the bundled middleware an agent carries."""
    out: list[ToolInfo] = []
    for mw in middleware:
        if mw.bundled:
            for name in BUILTIN_TOOLS.get(mw.name, []):
                out.append(ToolInfo(name=name, kind="builtin", bundled=True))
    return out


def _friendly_mw_name(mw) -> str:
    name = type(mw).__name__
    return name[: -len("Middleware")] if name.endswith("Middleware") else name


def middleware_labels(
    middleware,
    *,
    skills,
    memory,
    interrupt_on,
    has_subagents: bool,
    include_defaults: bool,
) -> list[MiddlewareInfo]:
    labels: list[MiddlewareInfo] = []
    # DeepAgents-bundled middleware, synthesised from configuration.
    if include_defaults:
        labels += [MiddlewareInfo("Planning"), MiddlewareInfo("Filesystem")]
    if has_subagents:
        labels.append(MiddlewareInfo("SubAgent"))
    if skills:
        labels.append(MiddlewareInfo("Skills"))
    if memory:
        labels.append(MiddlewareInfo("Memory"))
    if interrupt_on:
        labels.append(MiddlewareInfo("HITL"))
    # User-supplied middleware are not bundled.
    for mw in middleware or []:
        labels.append(MiddlewareInfo(_friendly_mw_name(mw), bundled=False))
    # de-duplicate by name while preserving order
    seen: set[str] = set()
    out: list[MiddlewareInfo] = []
    for label in labels:
        if label.name not in seen:
            seen.add(label.name)
            out.append(label)
    return out


def _collapse_mcp_tools(tools: list[ToolInfo]) -> list[ToolInfo]:
    """Collapse MCP tools to a single existence badge per server, OR-ing the
    gated flag, so a server exposing several tools yields one badge."""
    out: list[ToolInfo] = []
    index_by_server: dict[str, int] = {}
    for t in tools:
        if t.kind == "mcp":
            existing = index_by_server.get(t.mcp_server)
            if existing is not None:
                if t.gated:
                    out[existing].gated = True
                continue
            index_by_server[t.mcp_server] = len(out)
        out.append(t)
    return out


def _subagent_model(spec: dict) -> AgentModel:
    interrupt_on = spec.get("interrupt_on") or {}
    gated = set(interrupt_on.keys())
    tools = _collapse_mcp_tools([tool_info(t, gated) for t in (spec.get("tools") or [])])
    middleware = middleware_labels(
        spec.get("middleware"),
        skills=spec.get("skills"),
        memory=spec.get("memory"),
        interrupt_on=interrupt_on,
        has_subagents=False,
        include_defaults=False,
    )
    return AgentModel(
        name=str(spec.get("name", "subagent")),
        model_name=model_label(spec.get("model")),
        tools=tools + builtin_tools(middleware),
        middleware=middleware,
        hitl_gates=list(interrupt_on.keys()),
        skills=[str(s) for s in (spec.get("skills") or [])],
        memory=[str(m) for m in (spec.get("memory") or [])],
        permissions=permission_labels(spec.get("permissions")),
        mcp_servers=sorted({t.mcp_server for t in tools if t.mcp_server}),
    )


def build_model_from_kwargs(
    kwargs: dict,
    *,
    default_name: str = "agent",
    include_general_purpose: bool = True,
) -> AgentModel:
    interrupt_on = kwargs.get("interrupt_on") or {}
    gated = set(interrupt_on.keys())
    tools = _collapse_mcp_tools([tool_info(t, gated) for t in (kwargs.get("tools") or [])])
    subagent_specs = kwargs.get("subagents") or []
    has_subagents = bool(subagent_specs)
    model_name = model_label(kwargs.get("model"))

    middleware = middleware_labels(
        kwargs.get("middleware"),
        skills=kwargs.get("skills"),
        memory=kwargs.get("memory"),
        interrupt_on=interrupt_on,
        has_subagents=has_subagents,
        include_defaults=True,
    )
    included = builtin_tools(middleware)

    subagents = [_subagent_model(s) for s in subagent_specs]
    if include_general_purpose and has_subagents:
        # general-purpose inherits the main agent's model and its custom tools (graph.py
        # passes `tools=_tools`). It is built with plain create_agent — its middleware
        # stack has Planning + Filesystem but NOT SubAgentMiddleware, so it does NOT get
        # the `task` tool and cannot spawn further subagents. Its built-ins therefore
        # exclude SubAgent's `task`.
        gp_middleware = [m for m in middleware if m.name in {"Planning", "Filesystem", "Skills"}]
        subagents.append(
            AgentModel(
                name="general-purpose",
                model_name=model_name,
                tools=tools + builtin_tools(gp_middleware),
                is_builtin=True,
            )
        )

    return AgentModel(
        name=str(kwargs.get("name") or default_name),
        model_name=model_name,
        tools=tools + included,
        middleware=middleware,
        hitl_gates=list(interrupt_on.keys()),
        skills=[str(s) for s in (kwargs.get("skills") or [])],
        memory=[str(m) for m in (kwargs.get("memory") or [])],
        permissions=permission_labels(kwargs.get("permissions")),
        mcp_servers=sorted({t.mcp_server for t in tools if t.mcp_server}),
        subagents=subagents,
    )
