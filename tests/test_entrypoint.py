from pathlib import Path

import pytest

from deepagents_viz.entrypoint import load_agent_model, parse_target

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _restore_create_deep_agent():
    """Snapshot and restore deepagents.create_deep_agent so the patch never leaks
    into other test modules (load_agent_model installs it but never reverts it)."""
    import deepagents

    original = deepagents.create_deep_agent
    yield
    deepagents.create_deep_agent = original


def test_parse_target_file_attr(tmp_path):
    f = tmp_path / "agent.py"
    f.write_text("agent = 1\n")
    t = parse_target(f"{f}:agent")
    assert t.module_file == f
    assert t.attr == "agent"
    assert t.syspath_dirs[0] == f.parent


def test_parse_target_langgraph_dependencies(tmp_path):
    (tmp_path / "agent.py").write_text("agent = 1\n")
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": [".", ".."], "graphs": {"agent": "./agent.py:agent"}}'
    )
    t = parse_target(str(tmp_path))
    assert t.attr == "agent"
    assert t.graph_name == "agent"
    assert tmp_path.resolve() in [p.resolve() for p in t.syspath_dirs]
    assert tmp_path.parent.resolve() in [p.resolve() for p in t.syspath_dirs]


def test_load_module_level_agent():
    m = load_agent_model(str(FIXTURES / "simple"))
    assert m.name == "agent"  # no name= kwarg → falls back to graph name
    assert m.model_name == "anthropic:claude-sonnet-4-6"
    assert sorted(t.name for t in m.tools) == ["add", "danger"]
    assert m.hitl_gates == ["danger"]
    sub_names = [s.name for s in m.subagents]
    assert sub_names == ["researcher", "general-purpose"]
    assert m.subagents[0].hitl_gates == ["add"]
    assert "SubAgent" in m.middleware
    assert "~Planning/TODO" in m.middleware


def test_load_async_factory():
    m = load_agent_model(str(FIXTURES / "factory"))
    assert m.name == "factory-agent"
    assert [t.name for t in m.tools] == ["ping"]
