from types import SimpleNamespace

from deepagents_viz.extract import (
    build_model_from_kwargs,
    middleware_labels,
    model_label,
    permission_labels,
    tool_info,
)


def _fn_tool(name):
    return SimpleNamespace(name=name)


def _mcp_tool(server):
    return SimpleNamespace(name=f"{server}-tool", mcp_server=server)


def test_model_label_variants():
    assert model_label("anthropic:claude-haiku-4-5") == "anthropic:claude-haiku-4-5"
    assert model_label(SimpleNamespace(model="gpt-4.1")) == "gpt-4.1"
    assert model_label(None) == ""


def test_tool_info_function_and_gated():
    assert tool_info(_fn_tool("add"), set()).kind == "function"
    assert tool_info(_fn_tool("danger"), {"danger"}).gated is True


def test_tool_info_mcp():
    t = tool_info(_mcp_tool("mock-mail"), set())
    assert t.kind == "mcp"
    assert t.mcp_server == "mock-mail"


def test_middleware_labels_infers_and_marks_defaults():
    # Instantiate a throwaway class so type(mw).__name__ == "CodeInterpreterMiddleware".
    # (SimpleNamespace(__class__=...) would NOT work: __class__ is a data descriptor,
    # so type(mw) stays SimpleNamespace regardless of the kwarg.)
    code_interpreter_mw = type("CodeInterpreterMiddleware", (), {})()
    labels = middleware_labels(
        [code_interpreter_mw],
        skills=["/skills"],
        memory=["/AGENTS.md"],
        interrupt_on={"x": True},
        has_subagents=True,
        include_defaults=True,
    )
    assert "~Planning/TODO" in labels
    assert "~Filesystem" in labels
    assert any(l.startswith("Skills") for l in labels)
    assert any(l.startswith("Memory") for l in labels)
    assert "HITL" in labels
    assert "SubAgent" in labels
    assert "CodeInterpreter" in labels


def test_build_model_full_tree():
    subagent = {
        "name": "researcher",
        "description": "researches",
        "system_prompt": "…",
        "tools": [_fn_tool("search"), _fn_tool("save")],
        "model": "anthropic:claude-haiku-4-5",
        "interrupt_on": {"save": True},
    }
    kwargs = {
        "name": "editor",
        "model": "anthropic:claude-sonnet-4-6",
        "tools": [_fn_tool("compile"), _mcp_tool("mock-mail")],
        "subagents": [subagent],
        "interrupt_on": {"compile": True},
        "skills": ["/skills"],
    }
    m = build_model_from_kwargs(kwargs)

    assert m.name == "editor"
    assert m.model_name == "anthropic:claude-sonnet-4-6"
    assert m.hitl_gates == ["compile"]
    assert m.mcp_servers == ["mock-mail"]
    assert "SubAgent" in m.middleware

    names = [s.name for s in m.subagents]
    assert names == ["researcher", "general-purpose"]

    researcher = m.subagents[0]
    assert researcher.model_name == "anthropic:claude-haiku-4-5"
    gated = [t.name for t in researcher.tools if t.gated]
    assert gated == ["save"]

    gp = m.subagents[1]
    assert gp.is_builtin is True


def test_build_model_default_name_and_no_subagents():
    m = build_model_from_kwargs({"tools": [_fn_tool("a")]}, default_name="agent")
    assert m.name == "agent"
    assert m.subagents == []  # no synthetic general-purpose without subagents/task


def test_tool_info_mcp_gated():
    t = tool_info(SimpleNamespace(name="mail_create_draft", mcp_server="mail"), {"mail_create_draft"})
    assert t.kind == "mcp"
    assert t.mcp_server == "mail"
    assert t.gated is True


def test_subagent_populates_skills_and_memory():
    spec = {"name": "s", "tools": [], "skills": ["/skills"], "memory": ["/AGENTS.md"]}
    m = build_model_from_kwargs({"subagents": [spec]})
    sub = m.subagents[0]
    assert sub.skills == ["/skills"]
    assert sub.memory == ["/AGENTS.md"]


def test_model_label_model_name_fallback():
    # no .model attr, but has .model_name
    assert model_label(SimpleNamespace(model_name="foo")) == "foo"


def test_model_label_type_name_fallback():
    # object with neither .model nor .model_name -> class name
    weird = type("WeirdModel", (), {})()
    assert model_label(weird) == "WeirdModel"


def test_permission_labels():
    perm = SimpleNamespace(operations=["read", "write"], paths=["/x/**"], mode="allow")
    assert permission_labels([perm]) == ["allow read,write /x/**"]


def test_middleware_memory_sources_branch():
    mw = type("MemoryMiddleware", (), {})()
    mw.sources = ["/mem.md"]
    labels = middleware_labels(
        [mw], skills=None, memory=None, interrupt_on=None,
        has_subagents=False, include_defaults=False,
    )
    assert "Memory(/mem.md)" in labels


def test_middleware_labels_dedup():
    mw = type("MemoryMiddleware", (), {})()
    mw.sources = ["/a"]
    labels = middleware_labels(
        [mw], skills=None, memory=["/a"], interrupt_on=None,
        has_subagents=False, include_defaults=False,
    )
    assert labels.count("Memory(/a)") == 1


def test_build_model_collapses_duplicate_mcp_badges():
    m = build_model_from_kwargs(
        {"tools": [_mcp_tool("mail"), _mcp_tool("mail"), _fn_tool("x")]}
    )
    mcp = [t for t in m.tools if t.kind == "mcp"]
    assert len(mcp) == 1
    assert mcp[0].mcp_server == "mail"
    assert m.mcp_servers == ["mail"]


def test_collapse_mcp_merges_gated_flag():
    m = build_model_from_kwargs(
        {
            "tools": [
                SimpleNamespace(name="a", mcp_server="s"),
                SimpleNamespace(name="b", mcp_server="s"),
            ],
            "interrupt_on": {"b": True},
        }
    )
    mcp = [t for t in m.tools if t.kind == "mcp"]
    assert len(mcp) == 1
    assert mcp[0].gated is True  # gating from tool 'b' preserved after collapse
