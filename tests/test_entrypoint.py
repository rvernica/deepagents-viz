from pathlib import Path

import pytest

from deepagents_viz.entrypoint import load_agent_model, parse_target

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _restore_create_deep_agent():
    """Snapshot and restore deepagents.create_deep_agent so the patch never leaks
    into other test modules. Belt-and-suspenders: load_agent_model already
    reverts the patch in its own finally block, this fixture just guards
    against any future path that installs it without a matching revert."""
    import deepagents

    original = deepagents.create_deep_agent
    yield
    deepagents.create_deep_agent = original
    import deepagents_viz.intercept as _icpt
    _icpt._original_create_deep_agent = None


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


def test_parse_target_dir_without_langgraph(tmp_path):
    with pytest.raises(RuntimeError, match="No langgraph.json"):
        parse_target(str(tmp_path))


def test_parse_target_unrecognized(tmp_path):
    bogus = tmp_path / "thing.txt"
    bogus.write_text("x")
    with pytest.raises(RuntimeError, match="Cannot interpret target"):
        parse_target(str(bogus))


def test_parse_target_explicit_graph_selection(tmp_path):
    (tmp_path / "agent.py").write_text("agent = 1\nother = 2\n")
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"a": "./agent.py:agent", "b": "./agent.py:other"}}'
    )
    t = parse_target(str(tmp_path), graph="b")
    assert t.attr == "other"
    assert t.graph_name == "b"


def test_parse_target_missing_graph_name(tmp_path):
    (tmp_path / "agent.py").write_text("agent = 1\n")
    (tmp_path / "langgraph.json").write_text('{"graphs": {"a": "./agent.py:agent"}}')
    with pytest.raises(RuntimeError, match="not in"):
        parse_target(str(tmp_path), graph="nope")


def test_parse_target_bad_spec_no_colon(tmp_path):
    (tmp_path / "langgraph.json").write_text('{"graphs": {"a": "agent.py"}}')
    with pytest.raises(RuntimeError, match="path:attr"):
        parse_target(str(tmp_path))


def test_load_missing_attr_raises(tmp_path):
    (tmp_path / "agent.py").write_text("x = 1\n")
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./agent.py:nosuch"}}'
    )
    with pytest.raises(RuntimeError, match="not found"):
        load_agent_model(str(tmp_path))


def test_load_sync_factory(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from deepagents import create_deep_agent\n"
        "def build():\n"
        "    return create_deep_agent(model='m', tools=[], name='sync-built')\n"
    )
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./agent.py:build"}}'
    )
    m = load_agent_model(str(tmp_path))
    assert m.name == "sync-built"


def test_langgraph_missing_module_file_raises(tmp_path):
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./nope.py:agent"}}'
    )
    with pytest.raises(RuntimeError, match="does not exist"):
        parse_target(str(tmp_path))


def test_load_callable_object_factory(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from deepagents import create_deep_agent\n"
        "class Factory:\n"
        "    def __call__(self):\n"
        "        return create_deep_agent(model='m', tools=[], name='obj-built')\n"
        "make = Factory()\n"
    )
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./agent.py:make"}}'
    )
    m = load_agent_model(str(tmp_path))
    assert m.name == "obj-built"


def test_load_selects_correct_module_level_graph(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from deepagents import create_deep_agent\n"
        "a = create_deep_agent(model='ma', tools=[], name='AAA')\n"
        "b = create_deep_agent(model='mb', tools=[], name='BBB')\n"
    )
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"a": "./agent.py:a", "b": "./agent.py:b"}}'
    )
    assert load_agent_model(str(tmp_path), graph="a").name == "AAA"
    assert load_agent_model(str(tmp_path), graph="b").name == "BBB"


def test_load_factory_selects_returned_agent(tmp_path):
    # A factory that builds two agents and returns the FIRST must render the
    # first (index-tagged), not the last create_deep_agent call.
    (tmp_path / "agent.py").write_text(
        "from deepagents import create_deep_agent\n"
        "def make():\n"
        "    first = create_deep_agent(model='m1', tools=[], name='FIRST')\n"
        "    create_deep_agent(model='m2', tools=[], name='SECOND')\n"
        "    return first\n"
    )
    (tmp_path / "langgraph.json").write_text(
        '{"dependencies": ["."], "graphs": {"agent": "./agent.py:make"}}'
    )
    assert load_agent_model(str(tmp_path)).name == "FIRST"
