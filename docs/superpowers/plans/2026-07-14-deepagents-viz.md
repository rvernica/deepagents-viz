# DeepAgents-Viz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python CLI that renders a LangChain DeepAgents agent's architecture (subagent hierarchy, tools per agent, HITL gates, middleware) as a Mermaid diagram, extracted offline with no LLM keys or live services.

**Architecture:** Monkeypatch `create_deep_agent` before importing the target module so it records the fully-resolved kwargs and returns a `MagicMock` (never compiling a graph). Dummy env vars and a stubbed MCP client keep construction offline. A pure `build_model_from_kwargs` converts captured kwargs into an `AgentModel` data structure, which a Mermaid renderer turns into diagram text. Extraction and rendering are separated by the `AgentModel` boundary so a Graphviz/DOT renderer can be added later without touching extraction.

**Tech Stack:** Python ≥3.11 (stdlib only at runtime: `argparse`, `importlib`, `json`, `asyncio`, `dataclasses`, `unittest.mock`); `uv` for env/build; `pytest` for tests; `deepagents` + `langchain-core` as dev-only deps for the integration fixture.

## Global Constraints

- Python `>=3.11`.
- Distribution name `deepagents-viz`; import package `deepagents_viz`; console script `deepagents-viz`.
- **Zero runtime dependencies** — the tool runs inside the agent's own venv, which already provides `deepagents`. `[project.dependencies]` stays empty.
- Offline only: no network calls, no LLM invocation, no Node/browser. MCP is shown as an existence badge (per-server), never resolved to individual tools.
- Default output is stdout; `-o/--output` writes a file.
- Use long-form CLI flags (`--output`, `--graph`); short aliases allowed.
- Inferred/default middleware entries are prefixed `~` in output to distinguish them from middleware read directly from the call.

---

## File Structure

- `pyproject.toml` — uv project, build backend, dev deps, console script.
- `src/deepagents_viz/__init__.py` — package marker.
- `src/deepagents_viz/model.py` — `ToolInfo`, `AgentModel` dataclasses (the extraction↔render boundary).
- `src/deepagents_viz/render/__init__.py` — package marker.
- `src/deepagents_viz/render/mermaid.py` — `render(AgentModel) -> str`.
- `src/deepagents_viz/extract.py` — pure kwargs→`AgentModel` logic + helpers.
- `src/deepagents_viz/intercept.py` — dummy env, `create_deep_agent` patch + capture buffer, MCP stub.
- `src/deepagents_viz/entrypoint.py` — locate/parse target, set up sys.path, import + run factory, return `AgentModel`.
- `src/deepagents_viz/cli.py` — argparse, orchestration, output.
- `tests/test_model.py`, `tests/test_mermaid.py`, `tests/test_extract.py`, `tests/test_intercept.py`, `tests/test_entrypoint.py`, `tests/test_cli.py`.
- `tests/fixtures/simple/` and `tests/fixtures/factory/` — real fixture deep agents.
- `README.md`.

---

## Task 1: Project scaffold + data model

**Files:**
- Create: `pyproject.toml`
- Create: `src/deepagents_viz/__init__.py`
- Create: `src/deepagents_viz/model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ToolInfo(name: str, kind: Literal["function","mcp","builtin"]="function", gated: bool=False, mcp_server: str|None=None)`
  - `AgentModel(name: str, model_name: str="", tools: list[ToolInfo]=[], middleware: list[str]=[], hitl_gates: list[str]=[], skills: list[str]=[], memory: list[str]=[], permissions: list[str]=[], mcp_servers: list[str]=[], subagents: list[AgentModel]=[], is_builtin: bool=False)`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "deepagents-viz"
version = "0.1.0"
description = "Visualize LangChain DeepAgents architecture as a Mermaid diagram."
requires-python = ">=3.11"
dependencies = []

[project.scripts]
deepagents-viz = "deepagents_viz.cli:main"

[dependency-groups]
dev = ["pytest>=8", "deepagents", "langchain-core"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/deepagents_viz"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package markers**

`src/deepagents_viz/__init__.py`:

```python
"""deepagents-viz: render a DeepAgents architecture as a Mermaid diagram."""
```

- [ ] **Step 3: Write the failing test** — `tests/test_model.py`

```python
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.model'`

- [ ] **Step 5: Create `src/deepagents_viz/model.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ToolInfo:
    name: str
    kind: Literal["function", "mcp", "builtin"] = "function"
    gated: bool = False
    mcp_server: Optional[str] = None


@dataclass
class AgentModel:
    name: str
    model_name: str = ""
    tools: list[ToolInfo] = field(default_factory=list)
    middleware: list[str] = field(default_factory=list)
    hitl_gates: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    subagents: list["AgentModel"] = field(default_factory=list)
    is_builtin: bool = False
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_model.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/deepagents_viz/__init__.py src/deepagents_viz/model.py tests/test_model.py
git commit --message="feat: scaffold uv project and AgentModel data model"
```

---

## Task 2: Mermaid renderer

**Files:**
- Create: `src/deepagents_viz/render/__init__.py`
- Create: `src/deepagents_viz/render/mermaid.py`
- Test: `tests/test_mermaid.py`

**Interfaces:**
- Consumes: `AgentModel`, `ToolInfo` from `deepagents_viz.model`.
- Produces: `render(agent: AgentModel) -> str` — returns Mermaid `graph TD` text (trailing newline). Node ids are slugified (`[a-zA-Z0-9_]`); each agent is a `subgraph` containing an optional middleware node (`🧩 …`) and an optional tools node (`🔧 …`). MCP tools render as `🔌 MCP: <server>`. Gated tools get a ` ⚠` suffix and the containing tools node gets `:::gated`. The main agent connects to each subagent with `-->|task|`.

- [ ] **Step 1: Create `src/deepagents_viz/render/__init__.py`**

```python
"""Renderers that turn an AgentModel into diagram text."""
```

- [ ] **Step 2: Write the failing test** — `tests/test_mermaid.py`

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_mermaid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.render.mermaid'`

- [ ] **Step 4: Create `src/deepagents_viz/render/mermaid.py`**

```python
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
    if t.kind == "mcp":
        return f"🔌 MCP: {t.mcp_server}"
    return f"{t.name} ⚠" if t.gated else t.name


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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_mermaid.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add src/deepagents_viz/render/ tests/test_mermaid.py
git commit --message="feat: add Mermaid renderer for AgentModel"
```

---

## Task 3: Extractor (kwargs → AgentModel)

**Files:**
- Create: `src/deepagents_viz/extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: `AgentModel`, `ToolInfo`.
- Produces:
  - `model_label(model) -> str` — string models pass through; objects try `.model`/`.model_name` attrs, else class name; `None` → `""`.
  - `tool_info(tool, gated_names: set[str]) -> ToolInfo` — objects carrying a truthy `mcp_server` (or `_mcp_server`) attr become `kind="mcp"`; otherwise name from `.name` or `.__name__`, gated if the name is in `gated_names`.
  - `permission_labels(permissions) -> list[str]` — best-effort `"<mode> <ops> <paths>"` per rule.
  - `middleware_labels(middleware, *, skills, memory, interrupt_on, has_subagents, include_defaults) -> list[str]` — friendly labels from explicit middleware instances plus implied entries; when `include_defaults` is true, prepends `~Planning/TODO` and `~Filesystem`.
  - `build_model_from_kwargs(kwargs: dict, *, default_name: str="agent", include_general_purpose: bool=True) -> AgentModel` — builds the main agent from a captured `create_deep_agent` kwargs dict, recurses into `subagents` dicts, and appends a synthetic built-in `general-purpose` subagent when `include_general_purpose` and subagents/task are present.

- [ ] **Step 1: Write the failing test** — `tests/test_extract.py`

```python
from types import SimpleNamespace

from deepagents_viz.extract import (
    build_model_from_kwargs,
    middleware_labels,
    model_label,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_extract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.extract'`

- [ ] **Step 3: Create `src/deepagents_viz/extract.py`**

```python
from __future__ import annotations

from deepagents_viz.model import AgentModel, ToolInfo


def model_label(model) -> str:
    if model is None:
        return ""
    if isinstance(model, str):
        return model
    for attr in ("model", "model_name"):
        val = getattr(model, attr, None)
        if isinstance(val, str) and val:
            return val
    return type(model).__name__


def tool_info(tool, gated_names: set[str]) -> ToolInfo:
    server = getattr(tool, "mcp_server", None) or getattr(tool, "_mcp_server", None)
    if server:
        return ToolInfo(name=str(server), kind="mcp", mcp_server=str(server))
    name = getattr(tool, "name", None) or getattr(tool, "__name__", None) or repr(tool)
    return ToolInfo(name=str(name), kind="function", gated=str(name) in gated_names)


def permission_labels(permissions) -> list[str]:
    labels: list[str] = []
    for p in permissions or []:
        mode = getattr(p, "mode", "?")
        ops = ",".join(getattr(p, "operations", []) or [])
        paths = ",".join(getattr(p, "paths", []) or [])
        labels.append(f"{mode} {ops} {paths}".strip())
    return labels


def _friendly_mw_name(mw) -> str:
    name = type(mw).__name__
    label = name[:-len("Middleware")] if name.endswith("Middleware") else name
    if name == "MemoryMiddleware":
        sources = getattr(mw, "sources", None)
        if sources:
            return f"Memory({','.join(str(s) for s in sources)})"
    return label


def middleware_labels(
    middleware,
    *,
    skills,
    memory,
    interrupt_on,
    has_subagents: bool,
    include_defaults: bool,
) -> list[str]:
    labels: list[str] = []
    if include_defaults:
        labels += ["~Planning/TODO", "~Filesystem"]
    if has_subagents:
        labels.append("SubAgent")
    if skills:
        labels.append(f"Skills({','.join(str(s) for s in skills)})")
    if memory:
        labels.append(f"Memory({','.join(str(m) for m in memory)})")
    if interrupt_on:
        labels.append("HITL")
    for mw in middleware or []:
        labels.append(_friendly_mw_name(mw))
    # de-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for l in labels:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out


def _subagent_model(spec: dict) -> AgentModel:
    interrupt_on = spec.get("interrupt_on") or {}
    gated = set(interrupt_on.keys())
    tools = [tool_info(t, gated) for t in (spec.get("tools") or [])]
    return AgentModel(
        name=str(spec.get("name", "subagent")),
        model_name=model_label(spec.get("model")),
        tools=tools,
        middleware=middleware_labels(
            spec.get("middleware"),
            skills=spec.get("skills"),
            memory=spec.get("memory"),
            interrupt_on=interrupt_on,
            has_subagents=False,
            include_defaults=False,
        ),
        hitl_gates=list(interrupt_on.keys()),
        permissions=permission_labels(spec.get("permissions")),
        mcp_servers=sorted({t.mcp_server for t in tools if t.mcp_server}),
    )


def build_model_from_kwargs(
    kwargs: dict,
    *,
    default_name: str = "agent",
    include_general_purpose: bool = True,
) -> AgentModel:
    interrupt_on = kwargs.get("interrupt_on") or {}
    gated = set(interrupt_on.keys())
    tools = [tool_info(t, gated) for t in (kwargs.get("tools") or [])]
    subagent_specs = kwargs.get("subagents") or []
    has_subagents = bool(subagent_specs)

    subagents = [_subagent_model(s) for s in subagent_specs]
    if include_general_purpose and has_subagents:
        subagents.append(AgentModel(name="general-purpose", is_builtin=True))

    return AgentModel(
        name=str(kwargs.get("name") or default_name),
        model_name=model_label(kwargs.get("model")),
        tools=tools,
        middleware=middleware_labels(
            kwargs.get("middleware"),
            skills=kwargs.get("skills"),
            memory=kwargs.get("memory"),
            interrupt_on=interrupt_on,
            has_subagents=has_subagents,
            include_defaults=True,
        ),
        hitl_gates=list(interrupt_on.keys()),
        skills=[str(s) for s in (kwargs.get("skills") or [])],
        memory=[str(m) for m in (kwargs.get("memory") or [])],
        permissions=permission_labels(kwargs.get("permissions")),
        mcp_servers=sorted({t.mcp_server for t in tools if t.mcp_server}),
        subagents=subagents,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_extract.py -v`
Expected: PASS (6 passed)

Note: `test_middleware_labels_infers_and_marks_defaults` instantiates a throwaway class named `CodeInterpreterMiddleware` (so `type(mw).__name__` is that name); `_friendly_mw_name` strips the `Middleware` suffix to yield `CodeInterpreter`.

- [ ] **Step 5: Commit**

```bash
git add src/deepagents_viz/extract.py tests/test_extract.py
git commit --message="feat: add kwargs-to-AgentModel extractor"
```

---

## Task 4: Interception (dummy env, create_deep_agent patch, MCP stub)

**Files:**
- Create: `src/deepagents_viz/intercept.py`
- Test: `tests/test_intercept.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure mechanics).
- Produces:
  - `CAPTURED: list[dict]` — module-level buffer; each entry is the `kwargs` dict of one `create_deep_agent` call.
  - `set_dummy_env() -> None` — sets common provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`) to `"dummy"` only when unset.
  - `install_create_deep_agent_patch() -> None` — sets `deepagents.create_deep_agent` to a wrapper that appends its kwargs to `CAPTURED` and returns a `MagicMock()`. No-op (does not raise) if `deepagents` is not importable.
  - `MCPPlaceholder(name, mcp_server)` — object with `.name` and `.mcp_server` string attrs.
  - `install_mcp_stub() -> None` — if `langchain_mcp_adapters.client.MultiServerMCPClient` is importable, wraps `__init__` to record server names and replaces async `get_tools` to return one `MCPPlaceholder` per server (no network). No-op if not importable.
  - `reset() -> None` — clears `CAPTURED`.

- [ ] **Step 1: Write the failing test** — `tests/test_intercept.py`

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_intercept.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.intercept'`

- [ ] **Step 3: Create `src/deepagents_viz/intercept.py`**

```python
from __future__ import annotations

import os
from unittest.mock import MagicMock

CAPTURED: list[dict] = []

_DUMMY_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
)


def reset() -> None:
    CAPTURED.clear()


def set_dummy_env() -> None:
    for key in _DUMMY_KEYS:
        os.environ.setdefault(key, "dummy")


class MCPPlaceholder:
    """Stand-in for an MCP tool; carries only its originating server name."""

    def __init__(self, name: str, mcp_server: str):
        self.name = name
        self.mcp_server = mcp_server


def _record(*_args, **kwargs):
    CAPTURED.append(kwargs)
    return MagicMock()


def install_create_deep_agent_patch() -> None:
    try:
        import deepagents
    except Exception:
        return
    deepagents.create_deep_agent = _record


def install_mcp_stub() -> None:
    try:
        from langchain_mcp_adapters import client as mcp_client
    except Exception:
        return

    cls = mcp_client.MultiServerMCPClient
    original_init = cls.__init__

    def patched_init(self, connections=None, *args, **kwargs):
        self._captured_servers = list((connections or {}).keys())
        try:
            original_init(self, connections, *args, **kwargs)
        except Exception:
            pass

    async def patched_get_tools(self, *args, **kwargs):
        servers = getattr(self, "_captured_servers", [])
        return [MCPPlaceholder(name=s, mcp_server=s) for s in servers]

    cls.__init__ = patched_init
    cls.get_tools = patched_get_tools
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_intercept.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/deepagents_viz/intercept.py tests/test_intercept.py
git commit --message="feat: add interception (dummy env, create_deep_agent patch, MCP stub)"
```

---

## Task 5: Entrypoint loader (target parsing + import + run)

**Files:**
- Create: `src/deepagents_viz/entrypoint.py`
- Create: `tests/fixtures/simple/langgraph.json`
- Create: `tests/fixtures/simple/agent.py`
- Create: `tests/fixtures/factory/langgraph.json`
- Create: `tests/fixtures/factory/agent.py`
- Test: `tests/test_entrypoint.py`

**Interfaces:**
- Consumes: `intercept` (patches + `CAPTURED`), `build_model_from_kwargs`, `AgentModel`.
- Produces:
  - `Target(module_file: Path, attr: str, syspath_dirs: list[Path], graph_name: str)` — dataclass.
  - `parse_target(target: str, graph: str|None=None) -> Target` — accepts `file.py:attr`, a directory (finds `langgraph.json`), or a `langgraph.json` path. For `langgraph.json`, resolves the chosen graph's `path:attr`, and builds `syspath_dirs` = the module's own directory followed by each existing directory named in `dependencies` (resolved relative to the json).
  - `load_agent_model(target: str, graph: str|None=None) -> AgentModel` — installs env/patches, prepends `syspath_dirs` to `sys.path`, imports the module by file path, resolves `attr`; if it is a coroutine function, `asyncio.run`s it; if it is a plain callable and nothing has been captured yet, calls it; then builds an `AgentModel` from the last captured kwargs (raising `RuntimeError` if none were captured).

- [ ] **Step 1: Create the module-level fixture** — `tests/fixtures/simple/langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./agent.py:agent" }
}
```

`tests/fixtures/simple/agent.py`:

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool
def danger(x: str) -> str:
    """A gated operation."""
    return x


researcher = {
    "name": "researcher",
    "description": "Researches things.",
    "system_prompt": "You research.",
    "tools": [add],
    "model": "anthropic:claude-haiku-4-5",
    "interrupt_on": {"add": True},
}

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[add, danger],
    system_prompt="Main agent.",
    subagents=[researcher],
    interrupt_on={"danger": True},
)
```

- [ ] **Step 2: Create the async-factory fixture** — `tests/fixtures/factory/langgraph.json`

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./agent.py:make_graph" }
}
```

`tests/fixtures/factory/agent.py`:

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool


@tool
def ping() -> str:
    """Ping."""
    return "pong"


async def make_graph():
    return create_deep_agent(
        model="anthropic:claude-haiku-4-5",
        tools=[ping],
        system_prompt="Factory-built agent.",
        name="factory-agent",
    )
```

- [ ] **Step 3: Write the failing test** — `tests/test_entrypoint.py`

```python
from pathlib import Path

from deepagents_viz.entrypoint import load_agent_model, parse_target

FIXTURES = Path(__file__).parent / "fixtures"


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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_entrypoint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.entrypoint'`

- [ ] **Step 5: Create `src/deepagents_viz/entrypoint.py`**

```python
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from deepagents_viz import intercept
from deepagents_viz.extract import build_model_from_kwargs
from deepagents_viz.model import AgentModel


@dataclass
class Target:
    module_file: Path
    attr: str
    syspath_dirs: list[Path]
    graph_name: str


def _from_langgraph_json(json_path: Path, graph: str | None) -> Target:
    data = json.loads(json_path.read_text())
    graphs = data.get("graphs", {})
    if not graphs:
        raise RuntimeError(f"No graphs declared in {json_path}")
    graph_name = graph or next(iter(graphs))
    if graph_name not in graphs:
        raise RuntimeError(f"Graph {graph_name!r} not in {json_path}")
    spec = graphs[graph_name]  # e.g. "./agent.py:make_graph"
    rel_path, attr = spec.rsplit(":", 1)
    base = json_path.parent
    module_file = (base / rel_path).resolve()

    syspath_dirs = [module_file.parent]
    for dep in data.get("dependencies", []) or []:
        dep_dir = (base / dep).resolve()
        if dep_dir.is_dir() and dep_dir not in syspath_dirs:
            syspath_dirs.append(dep_dir)
    return Target(module_file, attr, syspath_dirs, graph_name)


def parse_target(target: str, graph: str | None = None) -> Target:
    if ":" in target and target.split(":", 1)[0].endswith(".py"):
        path_part, attr = target.split(":", 1)
        module_file = Path(path_part).resolve()
        return Target(module_file, attr, [module_file.parent], attr)

    p = Path(target)
    if p.is_dir():
        json_path = p / "langgraph.json"
        if not json_path.is_file():
            raise RuntimeError(f"No langgraph.json found in {p}")
        return _from_langgraph_json(json_path.resolve(), graph)
    if p.name == "langgraph.json":
        return _from_langgraph_json(p.resolve(), graph)
    raise RuntimeError(
        f"Cannot interpret target {target!r}: expected a dir with langgraph.json, "
        f"a langgraph.json path, or a 'file.py:attr' spec."
    )


def _import_module(module_file: Path):
    mod_name = f"_deepagents_viz_target_{module_file.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_agent_model(target: str, graph: str | None = None) -> AgentModel:
    t = parse_target(target, graph)

    intercept.set_dummy_env()
    intercept.install_create_deep_agent_patch()
    intercept.install_mcp_stub()
    intercept.reset()

    for d in reversed(t.syspath_dirs):
        sys.path.insert(0, str(d))

    module = _import_module(t.module_file)
    attr = getattr(module, t.attr, None)

    if inspect.iscoroutinefunction(attr):
        asyncio.run(attr())
    elif callable(attr) and not intercept.CAPTURED:
        attr()

    if not intercept.CAPTURED:
        raise RuntimeError(
            f"No create_deep_agent(...) call was captured for target {target!r}."
        )

    return build_model_from_kwargs(intercept.CAPTURED[-1], default_name=t.graph_name)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_entrypoint.py -v`
Expected: PASS (4 passed)

If `test_load_module_level_agent` fails at import with a `deepagents` error, confirm `uv sync` installed the dev group (`uv run python -c "import deepagents"`).

- [ ] **Step 7: Commit**

```bash
git add src/deepagents_viz/entrypoint.py tests/fixtures/ tests/test_entrypoint.py
git commit --message="feat: add entrypoint loader with langgraph.json + factory support"
```

---

## Task 6: CLI + README

**Files:**
- Create: `src/deepagents_viz/cli.py`
- Create: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_agent_model`, `render`.
- Produces: `main(argv: list[str]|None=None) -> int` — parses `target` (positional), `-o/--output PATH`, `--graph NAME`; loads the model, renders Mermaid, writes to the file or stdout; returns `0` on success, `2` on a handled `RuntimeError` (message to stderr).

- [ ] **Step 1: Write the failing test** — `tests/test_cli.py`

```python
from pathlib import Path

from deepagents_viz.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_stdout(capsys):
    code = main([str(FIXTURES / "simple")])
    assert code == 0
    out = capsys.readouterr().out
    assert out.startswith("graph TD")
    assert "-->|task| researcher" in out


def test_cli_writes_file(tmp_path):
    out_file = tmp_path / "diagram.mmd"
    code = main([str(FIXTURES / "simple"), "--output", str(out_file)])
    assert code == 0
    assert out_file.read_text().startswith("graph TD")


def test_cli_bad_target_returns_2(capsys):
    code = main(["/no/such/path"])
    assert code == 2
    assert "Cannot interpret target" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deepagents_viz.cli'`

- [ ] **Step 3: Create `src/deepagents_viz/cli.py`**

```python
from __future__ import annotations

import argparse
import sys

from deepagents_viz.entrypoint import load_agent_model
from deepagents_viz.render.mermaid import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deepagents-viz",
        description="Render a DeepAgents architecture as a Mermaid diagram.",
    )
    parser.add_argument(
        "target",
        help="Directory with langgraph.json, a langgraph.json path, or 'file.py:attr'.",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Write Mermaid to this file (default: stdout).",
    )
    parser.add_argument(
        "--graph", default=None,
        help="Graph name when langgraph.json declares more than one.",
    )
    args = parser.parse_args(argv)

    try:
        model = load_agent_model(args.target, args.graph)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    diagram = render(model)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(diagram)
    else:
        sys.stdout.write(diagram)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Create `README.md`**

````markdown
# deepagents-viz

Render a [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview.md)
agent's architecture — subagent hierarchy, tools per agent, HITL gates, and middleware —
as a Mermaid diagram. Extraction is **offline**: no LLM keys, no live services.

## How it works

`deepagents-viz` monkeypatches `create_deep_agent`, imports your agent module (running any
async factory), and records the resolved arguments instead of building a real graph. Dummy
env vars and a stubbed MCP client keep construction offline. MCP servers are shown as an
existence badge only.

## Install & run

Run it **inside your agent's own environment** (where `deepagents` is installed):

```bash
uv run --with deepagents-viz deepagents-viz path/to/agent_dir            # print Mermaid
uv run --with deepagents-viz deepagents-viz path/to/agent_dir -o out.mmd # write a file
uv run --with deepagents-viz deepagents-viz ./agent.py:make_graph        # target a factory
uv run --with deepagents-viz deepagents-viz . --graph agent              # pick a graph
```

`target` may be: a directory containing `langgraph.json`, a `langgraph.json` path, or a
`file.py:attr` spec.

## Viewing the diagram

- Paste the output into <https://mermaid.live> (Export → PNG/SVG), or
- drop it in a ```` ```mermaid ```` fenced block in a Markdown file on GitHub.

## Limitations

- Individual MCP tool names are not resolved (existence badge per server).
- `~`-prefixed middleware (e.g. `~Planning/TODO`, `~Filesystem`) is inferred from
  DeepAgents defaults rather than read from the call.
- Subagents built via nested `create_deep_agent` calls are not modelled (DeepAgents
  uses dicts).

## Roadmap

- Graphviz/DOT renderer for offline PNG/SVG from Python (via the native `dot` binary).
````

- [ ] **Step 6: Verify the whole suite and the console script**

Run: `uv run pytest -v`
Expected: PASS (all tests across all files)

Run: `uv run deepagents-viz tests/fixtures/simple`
Expected: Mermaid text on stdout starting with `graph TD`, containing `-->|task| researcher`.

- [ ] **Step 7: Commit**

```bash
git add src/deepagents_viz/cli.py tests/test_cli.py README.md
git commit --message="feat: add CLI, console script, and README"
```

---

## Manual verification (after Task 6)

Against a real course agent (has `deepagents` installed in its own venv):

```bash
# from the lca-deepagents python/ dir, in that project's venv:
uv run --with deepagents-viz deepagents-viz m5/sales_assistant -o sales.mmd
```

Confirm the diagram shows: `chinook-sales-assistant` main node; `task` edges to
`chinook-analyst`, `quote-reviewer`, `inbox-manager`, `genre-researcher` (present because a
dummy `TAVILY_API_KEY` is set), and `general-purpose`; `add_customer ⚠` and
`mail_create_draft ⚠` gated; a `🔌 MCP: mock-mail` badge; and middleware badges including
`CodeInterpreter`, `~Planning/TODO`, `~Filesystem`. Paste `sales.mmd` into mermaid.live to view.

> Note: the async `make_graph()` calls `MultiServerMCPClient(...).get_tools()`; the MCP stub
> returns per-server placeholders so no mail server needs to be running.

---

## Self-Review

**Spec coverage:**
- Runtime interception + stubbing → Task 4 (`intercept.py`), Task 5 (`load_agent_model`).
- Offline / no keys → dummy env + MagicMock return + MCP stub (Task 4).
- Entry-point discovery (langgraph.json, factory, file:attr) → Task 5 (`parse_target`, async run).
- sys.path from `dependencies` → Task 5 (`_from_langgraph_json`, tested).
- AgentModel data boundary → Task 1.
- Subagent hierarchy + built-in general-purpose → Task 3, rendered in Task 2.
- Tools per agent + MCP existence badge → Tasks 3 (extract) + 2 (render).
- HITL gates (`interrupt_on`) → Tasks 3 + 2 (`⚠`, `:::gated`).
- Middleware badges incl. inferred `~` defaults → Task 3 (`middleware_labels`) + 2.
- Mermaid output, stdout default, `-o`, `--graph`, long flags → Task 6.
- Graphviz/DOT out of scope, README roadmap → Task 6 README.

**Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step shows full code.

**Type consistency:** `build_model_from_kwargs`, `tool_info`, `model_label`, `middleware_labels`,
`load_agent_model`, `parse_target`, `render`, `main` signatures match across tasks; `Target`,
`AgentModel`, `ToolInfo`, `MCPPlaceholder`, `CAPTURED` used consistently.
