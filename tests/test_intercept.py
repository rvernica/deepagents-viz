import asyncio
import os

import pytest

from deepagents_viz import intercept


@pytest.fixture(autouse=True)
def _restore_create_deep_agent():
    """Snapshot and restore deepagents.create_deep_agent so the patch never leaks."""
    import deepagents

    original = deepagents.create_deep_agent
    yield
    deepagents.create_deep_agent = original
    intercept._original_create_deep_agent = None


def test_set_dummy_env_only_fills_unset(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    intercept.set_dummy_env()
    assert os.environ["ANTHROPIC_API_KEY"] == "real-key"
    assert os.environ["TAVILY_API_KEY"] == "dummy"


def test_mcp_placeholder_shape():
    p = intercept.MCPPlaceholder(name="mock-mail", mcp_server="mock-mail")
    assert p.name == "mock-mail"
    assert p.mcp_server == "mock-mail"


def test_patch_captures_kwargs_and_returns_mock():
    intercept.reset()
    intercept.install_create_deep_agent_patch()
    import deepagents

    result = deepagents.create_deep_agent(model="m", tools=[], system_prompt="p")
    assert result.anything.chained() is not None
    assert intercept.CAPTURED[-1]["model"] == "m"
    assert intercept.CAPTURED[-1]["system_prompt"] == "p"


def test_patch_captures_positional_model_arg():
    intercept.reset()
    intercept.install_create_deep_agent_patch()
    import deepagents

    deepagents.create_deep_agent("mymodel")
    assert intercept.CAPTURED[-1].get("model") == "mymodel"


def test_patch_mcp_class_returns_offline_placeholders():
    class FakeClient:
        def __init__(self, connections=None):
            self.connections = connections

    intercept._patch_mcp_class(FakeClient)
    client = FakeClient({"mock-mail": {}, "other": {}})
    tools = asyncio.run(client.get_tools())
    assert sorted(t.mcp_server for t in tools) == ["mock-mail", "other"]
    assert all(isinstance(t, intercept.MCPPlaceholder) for t in tools)


def test_install_is_idempotent_preserves_signature():
    intercept.reset()
    intercept.install_create_deep_agent_patch()
    intercept.install_create_deep_agent_patch()  # second call must be a no-op
    import deepagents

    deepagents.create_deep_agent("mymodel")  # positional normalization still works
    assert intercept.CAPTURED[-1].get("model") == "mymodel"


def test_uninstall_restores_original():
    import deepagents

    before = deepagents.create_deep_agent
    intercept.install_create_deep_agent_patch()
    assert deepagents.create_deep_agent is not before
    intercept.uninstall_create_deep_agent_patch()
    assert deepagents.create_deep_agent is before


def test_unpatch_mcp_class_restores():
    class FakeClient:
        def __init__(self, connections=None):
            self.connections = connections

        async def get_tools(self):
            return ["real"]

    orig_init = FakeClient.__init__
    orig_get = FakeClient.get_tools
    intercept._patch_mcp_class(FakeClient)
    assert FakeClient.__init__ is not orig_init
    intercept._patch_mcp_class(FakeClient)  # idempotent: no double-wrap
    intercept._unpatch_mcp_class(FakeClient)
    assert FakeClient.__init__ is orig_init
    assert FakeClient.get_tools is orig_get
