import os

from deepagents_viz import intercept


def test_set_dummy_env_only_fills_unset(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    intercept.set_dummy_env()
    assert os.environ["ANTHROPIC_API_KEY"] == "real-key"  # preserved
    assert os.environ["TAVILY_API_KEY"] == "dummy"  # filled


def test_mcp_placeholder_shape():
    p = intercept.MCPPlaceholder(name="mock-mail", mcp_server="mock-mail")
    assert p.name == "mock-mail"
    assert p.mcp_server == "mock-mail"


def test_patch_captures_kwargs_and_returns_mock():
    intercept.reset()
    intercept.install_create_deep_agent_patch()
    import deepagents

    result = deepagents.create_deep_agent(model="m", tools=[], system_prompt="p")
    # returned object is a permissive stand-in, not a real graph
    assert result.anything.chained() is not None
    assert intercept.CAPTURED[-1]["model"] == "m"
    assert intercept.CAPTURED[-1]["system_prompt"] == "p"
