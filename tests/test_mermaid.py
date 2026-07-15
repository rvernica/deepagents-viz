from deepagents_viz.model import AgentModel, ToolInfo
from deepagents_viz.render.mermaid import render


def _main():
    return AgentModel(
        name="chinook-sales-assistant",
        model_name="anthropic:claude-sonnet-4-6",
        tools=[
            ToolInfo(name="markdown_to_html"),
            ToolInfo(name="mock-mail", kind="mcp", mcp_server="mock-mail"),
        ],
        middleware=["~Planning/TODO", "~Filesystem", "SubAgent"],
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
    assert out.startswith("graph TD")
    assert "classDef gated" in out


def test_task_edges_to_each_subagent():
    out = render(_main())
    assert "-->|task| chinook_analyst" in out
    assert "-->|task| general_purpose" in out


def test_gated_tool_marked_and_styled():
    out = render(_main())
    assert "add_customer ⚠" in out
    assert ":::gated" in out


def test_mcp_existence_badge():
    out = render(_main())
    assert "🔌 MCP: mock-mail" in out


def test_middleware_and_builtin_label():
    out = render(_main())
    assert "🧩 ~Planning/TODO · ~Filesystem · SubAgent" in out
    assert "general-purpose (built-in, inherits main tools)" in out
