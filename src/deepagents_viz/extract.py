from __future__ import annotations

from deepagents_viz.model import AgentModel, ToolInfo


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


def _friendly_mw_name(mw) -> str:
    name = type(mw).__name__
    label = name[:-len("Middleware")] if name.endswith("Middleware") else name
    if name == "MemoryMiddleware":
        sources = getattr(mw, "sources", None)
        if sources:
            return f"Memory({','.join(str(s) for s in sources)})"
    return label


def middleware_labels(
    middleware,
    *,
    skills,
    memory,
    interrupt_on,
    has_subagents: bool,
    include_defaults: bool,
) -> list[str]:
    labels: list[str] = []
    if include_defaults:
        labels += ["~Planning/TODO", "~Filesystem"]
    if has_subagents:
        labels.append("SubAgent")
    if skills:
        labels.append(f"Skills({','.join(str(s) for s in skills)})")
    if memory:
        labels.append(f"Memory({','.join(str(m) for m in memory)})")
    if interrupt_on:
        labels.append("HITL")
    for mw in middleware or []:
        labels.append(_friendly_mw_name(mw))
    # de-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def _subagent_model(spec: dict) -> AgentModel:
    interrupt_on = spec.get("interrupt_on") or {}
    gated = set(interrupt_on.keys())
    tools = [tool_info(t, gated) for t in (spec.get("tools") or [])]
    return AgentModel(
        name=str(spec.get("name", "subagent")),
        model_name=model_label(spec.get("model")),
        tools=tools,
        middleware=middleware_labels(
            spec.get("middleware"),
            skills=spec.get("skills"),
            memory=spec.get("memory"),
            interrupt_on=interrupt_on,
            has_subagents=False,
            include_defaults=False,
        ),
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
    tools = [tool_info(t, gated) for t in (kwargs.get("tools") or [])]
    subagent_specs = kwargs.get("subagents") or []
    has_subagents = bool(subagent_specs)

    subagents = [_subagent_model(s) for s in subagent_specs]
    if include_general_purpose and has_subagents:
        subagents.append(AgentModel(name="general-purpose", is_builtin=True))

    return AgentModel(
        name=str(kwargs.get("name") or default_name),
        model_name=model_label(kwargs.get("model")),
        tools=tools,
        middleware=middleware_labels(
            kwargs.get("middleware"),
            skills=kwargs.get("skills"),
            memory=kwargs.get("memory"),
            interrupt_on=interrupt_on,
            has_subagents=has_subagents,
            include_defaults=True,
        ),
        hitl_gates=list(interrupt_on.keys()),
        skills=[str(s) for s in (kwargs.get("skills") or [])],
        memory=[str(m) for m in (kwargs.get("memory") or [])],
        permissions=permission_labels(kwargs.get("permissions")),
        mcp_servers=sorted({t.mcp_server for t in tools if t.mcp_server}),
        subagents=subagents,
    )
