from deepagents_viz.model import AgentModel, ToolInfo


def test_toolinfo_defaults():
    t = ToolInfo(name="add")
    assert t.kind == "function"
    assert t.gated is False
    assert t.mcp_server is None


def test_agentmodel_defaults_are_independent():
    a = AgentModel(name="main")
    b = AgentModel(name="other")
    a.tools.append(ToolInfo(name="x"))
    assert a.model_name == ""
    assert b.tools == []  # default lists must not be shared
    assert a.subagents == []
