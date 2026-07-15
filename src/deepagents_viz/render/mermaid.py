from __future__ import annotations

import re

from deepagents_viz.model import AgentModel, ToolInfo


def _nid(name: str) -> str:
    """Slugify an agent name into a Mermaid-safe node id."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_")
    return slug or "n"


def _esc(text: str) -> str:
    """Escape a Mermaid label (used inside double quotes)."""
    return text.replace('"', "'")


def _tool_label(t: ToolInfo) -> str:
    label = f"🔌 MCP: {t.mcp_server}" if t.kind == "mcp" else t.name
    return f"{label} ⚠" if t.gated else label


def _emit_agent(a: AgentModel, lines: list[str]) -> None:
    nid = _nid(a.name)
    if a.is_builtin:
        label = f"{a.name} (built-in, inherits main tools)"
    elif a.model_name:
        label = f"{a.name} · {a.model_name}"
    else:
        label = a.name
    lines.append(f'  subgraph {nid}["{_esc(label)}"]')
    if a.middleware:
        lines.append(f'    {nid}_mw["🧩 {_esc(" · ".join(a.middleware))}"]')
    if a.tools:
        tools_txt = " · ".join(_tool_label(t) for t in a.tools)
        suffix = ":::gated" if any(t.gated for t in a.tools) else ""
        lines.append(f'    {nid}_t["🔧 {_esc(tools_txt)}"]{suffix}')
    lines.append("  end")


def render(agent: AgentModel) -> str:
    lines: list[str] = ["graph TD", "  classDef gated stroke:#c00,stroke-width:2px;"]
    _emit_agent(agent, lines)
    for sub in agent.subagents:
        lines.append(f"  {_nid(agent.name)} -->|task| {_nid(sub.name)}")
        _emit_agent(sub, lines)
    return "\n".join(lines) + "\n"
