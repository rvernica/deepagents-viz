from deepagents_viz.model import AgentModel, MiddlewareInfo, ToolInfo
from deepagents_viz.render.mermaid import BUNDLED, render


def _main():
    return AgentModel(
        name="chinook-sales-assistant",
        model_name="anthropic:claude-sonnet-4-6",
        tools=[
            ToolInfo(name="markdown_to_html"),
            ToolInfo(name="mock-mail", kind="mcp", mcp_server="mock-mail"),
        ],
        middleware=[
            MiddlewareInfo("Planning"),
            MiddlewareInfo("Filesystem"),
            MiddlewareInfo("SubAgent"),
        ],
        mcp_servers=["mock-mail"],
        subagents=[
            AgentModel(
                name="chinook-analyst",
                model_name="anthropic:claude-haiku-4-5",
                tools=[
                    ToolInfo(name="query_chinook"),
                    ToolInfo(name="add_customer", gated=True),
                ],
                hitl_gates=["add_customer"],
            ),
            AgentModel(name="general-purpose", is_builtin=True),
        ],
    )


def test_header_and_classdef():
    out = render(_main())
    assert "graph TD" in out
    assert "classDef mwBox" in out
    assert "classDef toolBox" in out


def test_boxes_are_pastel_and_thick_bordered():
    out = render(_main())
    # light blue agent box, light yellow middleware, light green tools — all 3px borders
    assert "fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px" in out
    assert "fill:#fff2cc,stroke:#d6b656,stroke-width:3px" in out
    assert "fill:#d5e8d4,stroke:#82b366,stroke-width:3px" in out


def test_text_color_pinned_dark_for_github_dark_mode():
    out = render(_main())
    # GitHub renders Mermaid with a theme chosen from the viewer's color scheme; its dark
    # theme would drive default text light, unreadable on our light pastels. Every styled
    # element must pin dark text so titles/labels stay legible in both light and dark.
    assert "fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a" in out  # agent
    assert "fill:#fff2cc,stroke:#d6b656,stroke-width:3px,color:#1a1a1a" in out  # middleware
    assert "fill:#d5e8d4,stroke:#82b366,stroke-width:3px,color:#1a1a1a" in out  # tools


def test_task_edges_to_each_subagent():
    out = render(_main())
    assert '-->|"sub-agent (task)"| chinook_analyst' in out
    assert '-->|"sub-agent (task)"| general_purpose' in out


def test_gated_tool_marked_with_red_warning_and_hitl():
    out = render(_main())
    # red warning-triangle prefix, (HITL) postfix, and no red-border classDef
    assert "<span style='color:#c00'>⚠</span> add_customer (HITL)" in out
    assert ":::gated" not in out
    assert "classDef gated" not in out


def test_mcp_existence_badge():
    out = render(_main())
    assert "🔌 mock-mail (MCP)" in out


def test_agent_title_splits_name_and_model():
    out = render(_main())
    assert "chinook-sales-assistant<br/>🧠 anthropic:claude-sonnet-4-6" in out


def test_middleware_box_bold_title_and_bundled_prefix():
    out = render(_main())
    # bold title, one entry per line, default entries prefixed with the bundled marker
    expected = (
        f"🧩 <b>Middleware</b><br/>{BUNDLED} Planning<br/>"
        f"{BUNDLED} Filesystem<br/>{BUNDLED} SubAgent"
    )
    assert expected in out


def test_builtin_agent_prefixed_with_bundled_marker():
    out = render(_main())
    assert f'general_purpose["{BUNDLED} general-purpose"]' in out


def test_tools_box_bold_title():
    out = render(_main())
    assert "🔧 <b>Tools</b><br/>markdown_to_html<br/>🔌 mock-mail (MCP)" in out


def test_boxes_are_left_aligned():
    out = render(_main())
    assert "<div style='text-align:left'>🧩 <b>Middleware</b>" in out
    assert "<div style='text-align:left'>🔧 <b>Tools</b>" in out


def test_init_directive_gives_title_margin_and_tight_padding():
    out = render(_main())
    assert out.startswith("%%{init:")
    assert "subGraphTitleMargin" in out
    assert "'padding': 4" in out


def test_bundled_tool_gets_prefix():
    a = AgentModel(name="x", tools=[ToolInfo(name="ls", kind="builtin", bundled=True)])
    out = render(a)
    assert f"{BUNDLED} ls" in out


def test_gated_mcp_tool_gets_marker():
    a = AgentModel(
        name="inbox",
        tools=[ToolInfo(name="mail", kind="mcp", mcp_server="mock-mail", gated=True)],
    )
    out = render(a)
    assert "<span style='color:#c00'>⚠</span> 🔌 mock-mail (MCP) (HITL)" in out


def test_unmatched_hitl_gate_surfaced_as_own_line():
    # An MCP-targeted gate: the tool name isn't among the visible tools (only a per-server
    # MCP badge), so it must appear as its own gated line rather than being dropped.
    a = AgentModel(
        name="inbox-manager",
        tools=[ToolInfo(name="mock-mail", kind="mcp", mcp_server="mock-mail")],
        hitl_gates=["mail_create_draft"],
    )
    out = render(a)
    assert "🔌 mock-mail (MCP)" in out
    assert "<span style='color:#c00'>⚠</span> mail_create_draft (HITL)" in out


def test_function_tool_gate_not_duplicated():
    # A gate matching a visible function tool renders once (on that tool), not twice.
    a = AgentModel(
        name="a",
        tools=[ToolInfo(name="add_customer", gated=True)],
        hitl_gates=["add_customer"],
    )
    out = render(a)
    assert out.count("add_customer (HITL)") == 1
