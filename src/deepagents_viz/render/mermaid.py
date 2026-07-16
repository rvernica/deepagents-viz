from __future__ import annotations

import re

from deepagents_viz.model import AgentModel, MiddlewareInfo, ToolInfo

# Emoji prefixing DeepAgents-bundled (default) middleware, built-in tools, and the
# built-in general-purpose subagent. Swap for ✅ / 🎁 / ⭐ to taste.
BUNDLED = "📦"

# Pastel fills paired with a slightly darker border of the same hue.
AGENT_FILL, AGENT_STROKE = "#dae8fc", "#6c8ebf"  # light blue
MW_FILL, MW_STROKE = "#fff2cc", "#d6b656"  # light yellow
TOOL_FILL, TOOL_STROKE = "#d5e8d4", "#82b366"  # light green
BORDER = "3px"

# Force dark text on every styled element. Fills are always light, but GitHub renders
# Mermaid with a theme chosen from the viewer's color scheme; its dark theme drives the
# default text color light, which is unreadable on our light pastels. Pinning the text
# color keeps titles and labels legible in both GitHub light and dark modes.
TEXT = "#1a1a1a"

# Extra breathing room under the (two-line) subgraph titles so they never overlap the
# first inner box; small node padding so each box hugs its content, which keeps the
# left-aligned titles pinned to the top-left corner instead of floating in the middle.
INIT = "%%{init: {'flowchart': {'subGraphTitleMargin': {'top': 6, 'bottom': 16}, 'padding': 4}}}%%"


def _nid(name: str) -> str:
    """Slugify an agent name into a Mermaid-safe node id."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_")
    return slug or "n"


def _esc(text: str) -> str:
    """Escape a Mermaid label (used inside double quotes)."""
    return text.replace('"', "'")


def _tool_label(t: ToolInfo) -> str:
    label = f"🔌 {t.mcp_server} (MCP)" if t.kind == "mcp" else t.name
    if t.gated:
        # Red warning-triangle prefix + (HITL) postfix; no red box border.
        return f"<span style='color:#c00'>⚠</span> {label} (HITL)"
    if t.bundled:
        return f"{BUNDLED} {label}"
    return label


def _mw_label(m: MiddlewareInfo) -> str:
    return f"{BUNDLED} {m.name}" if m.bundled else m.name


def _left(body: str) -> str:
    """Left-align every line of a multi-line node label.

    Combined with the small node padding set in INIT, the box hugs its content so the
    title lands in the top-left corner.
    """
    return f"<div style='text-align:left'>{body}</div>"


def _emit_agent(a: AgentModel, lines: list[str], styles: list[str]) -> None:
    nid = _nid(a.name)
    # Agent name on line one (built-in agents get the bundled prefix); model, if any,
    # alone on line two with the brain emoji.
    title = f"{BUNDLED} {a.name}" if a.is_builtin else a.name
    if a.model_name:
        title += f"<br/>🧠 {a.model_name}"
    lines.append(f'  subgraph {nid}["{_esc(title)}"]')
    if a.middleware:
        body = "🧩 <b>Middleware</b><br/>" + "<br/>".join(_esc(_mw_label(m)) for m in a.middleware)
        lines.append(f'    {nid}_mw["{_left(body)}"]:::mwBox')
    # HITL gates that don't match a visible tool are almost certainly on an MCP tool
    # (whose individual names we never resolve — the badge is per server). Surface them
    # as their own gated line so the gate isn't silently dropped.
    visible = {t.name for t in a.tools}
    unmatched = [ToolInfo(name=g, gated=True) for g in a.hitl_gates if g not in visible]
    tool_entries = a.tools + unmatched
    if tool_entries:
        body = "🔧 <b>Tools</b><br/>" + "<br/>".join(_esc(_tool_label(t)) for t in tool_entries)
        lines.append(f'    {nid}_t["{_left(body)}"]:::toolBox')
    lines.append("  end")
    styles.append(
        f"  style {nid} fill:{AGENT_FILL},stroke:{AGENT_STROKE},stroke-width:{BORDER},color:{TEXT};"
    )


def render(agent: AgentModel) -> str:
    lines: list[str] = [
        INIT,
        "graph TD",
        f"  classDef mwBox fill:{MW_FILL},stroke:{MW_STROKE},stroke-width:{BORDER},color:{TEXT};",
        f"  classDef toolBox fill:{TOOL_FILL},stroke:{TOOL_STROKE},stroke-width:{BORDER},color:{TEXT};",
    ]
    styles: list[str] = []
    _emit_agent(agent, lines, styles)
    for sub in agent.subagents:
        lines.append(f'  {_nid(agent.name)} -->|"sub-agent (task)"| {_nid(sub.name)}')
        _emit_agent(sub, lines, styles)
    return "\n".join(lines + styles) + "\n"
