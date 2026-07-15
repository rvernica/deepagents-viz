# DeepAgents-Viz — Design

**Date:** 2026-07-14
**Status:** Approved (pending spec review)

## Goal

A Python CLI tool that renders a [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview.md)
agent's architecture as a **Mermaid** diagram. The diagram shows:

- the **subagent hierarchy** (main agent → subagents),
- each agent's **tools**,
- **HITL gates** (human-in-the-loop approval on specific tools),
- **middleware** attached to each agent (Planning/TODO, Filesystem, HITL, Memory, CodeInterpreter, …).

The tool inspects the agent **offline**: no LLM/API keys and no live services are required.

## Approach: intercept, don't run

Building a deep agent is an offline operation — `create_deep_agent(...)` assembles and compiles a
LangGraph but never calls the LLM. Model objects (e.g. `init_chat_model("anthropic:...")`) are
constructed lazily and do not hit the provider API until the agent is *invoked*, which this tool
never does.

The extraction technique is **monkeypatch `create_deep_agent`**: we replace it with a wrapper that
records the fully-resolved keyword arguments at call time, then delegates to the real function and
returns its result so any factory code continues to work. Captured kwargs:

`model`, `tools`, `subagents`, `middleware`, `interrupt_on`, `skills`, `memory`, `permissions`, `name`.

Because DeepAgents subagents are plain `dict`s (not nested `create_deep_agent` calls), a single
interception captures the entire tree.

To make construction robust without keys or live services, before importing the target module we:

1. **Set dummy environment variables** (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`)
   so model construction never trips and env-gated branches render. This renders the **maximal**
   configuration of the graph. Done automatically in v1.
2. **Stub MCP.** `MultiServerMCPClient.__init__` is wrapped to capture the server connection names,
   and `get_tools()` is stubbed to return a placeholder tool tagged with its server name (no network
   call). MCP is shown as an existence badge only — individual MCP tool names are not resolved.

## Entry-point discovery

Primary path: read `langgraph.json` → `graphs`, e.g. `{"agent": "./agent.py:make_graph"}`.
Import the module, resolve the named attribute:

- **Async factory** (`async def make_graph()`): run via `asyncio.run()` with stubs already installed.
- **Sync factory**: call it.
- **Module-level compiled graph**: the interception already fired during import.

The CLI also accepts:

- a direct `path/to/file.py:attr` spec,
- a directory (auto-discover `langgraph.json` within it),
- a `langgraph.json` file path.

If `langgraph.json` declares multiple graphs, a `--graph <name>` flag selects one (default: first).

## Modules (uv project, `src/` layout)

```
deepagents-viz/
  pyproject.toml              # uv project; console script: deepagents-viz
  src/deepagents_viz/
    __init__.py
    cli.py                    # argparse, orchestration, output
    entrypoint.py             # locate/load graph (langgraph.json | file:attr), run factory
    intercept.py              # monkeypatch create_deep_agent, stub MCP, set dummy env
    model.py                  # AgentModel / ToolInfo dataclasses (the boundary)
    render/
      __init__.py
      mermaid.py              # AgentModel -> mermaid text
  tests/
    fixtures/                 # small fixture deep agent(s)
    test_model.py
    test_mermaid.py
    test_intercept.py
  README.md
```

Extraction produces a pure-data `AgentModel`; the renderer consumes only that. This keeps the two
sides independently testable and leaves room for a graphviz/excalidraw renderer later without
touching extraction.

## Data model

**`ToolInfo`**
- `name: str`
- `kind: Literal["function", "mcp", "builtin"]`
- `gated: bool` — true if named in an `interrupt_on` for its agent
- `mcp_server: str | None` — set when `kind == "mcp"`

**`AgentModel`**
- `name: str`
- `model_name: str` — best-effort human label (e.g. `anthropic:claude-haiku-4-5`)
- `tools: list[ToolInfo]`
- `middleware: list[str]` — display labels; inferred entries are marked (see below)
- `hitl_gates: list[str]` — tool names gated via `interrupt_on`
- `skills: list[str]`
- `memory: list[str]`
- `permissions: list[str]` — human-readable summary of FilesystemPermission rules
- `mcp_servers: list[str]`
- `subagents: list[AgentModel]`
- `is_builtin: bool` — true for the always-present `general-purpose` subagent

## Element mapping

- **Hierarchy** — main agent → each subagent via a `task` edge. Include the always-present built-in
  `general-purpose` subagent, marked as inheriting the main agent's tools.
- **Tools** — from each agent's `tools=` list. Tool name taken from the LangChain tool's `.name`
  (fallback: function `__name__`). MCP tools are collapsed into one `🔌 MCP: <server>` badge per
  server. Middleware-provided tools (`ls`/`read_file`/`write_file`, `task`, `write_todos`) are **not**
  listed as tools — they are represented by middleware badges instead.
- **HITL** — tools named in `interrupt_on` get a `⚠` marker and a distinct Mermaid style class.
- **Middleware** — union of:
  - explicit `middleware=` entries (e.g. `CodeInterpreterMiddleware`, `MemoryMiddleware`),
  - kwargs-implied middleware: `Skills` from `skills=`, `Memory` from `memory=`, `HITL` from
    `interrupt_on`, `SubAgent` from `subagents=`,
  - inferred DeepAgents defaults always present on a deep agent: `Planning/TODO`, `Filesystem`.

  Inferred/default entries are visually marked (e.g. a `~` prefix or note) so the diagram is honest
  about what was read from the call versus assumed from framework defaults.

## Sample output (sales_assistant)

```mermaid
graph TD
  classDef gated stroke:#c00,stroke-width:2px;
  subgraph main["chinook-sales-assistant · sonnet-4-6"]
    m_mw["🧩 ~Planning/TODO · ~Filesystem · SubAgent · Skills(/skills) · Memory(/AGENTS.md) · CodeInterpreter"]
    m_t["🔧 markdown_to_html · render_pie_chart · 🔌 MCP: mock-mail"]
  end
  main -->|task| analyst
  main -->|task| reviewer
  main -->|task| inbox
  main -->|task| genre
  main -->|task| general
  subgraph analyst["chinook-analyst · haiku"]
    a_t["🔧 query_chinook · introspect_schema · add_customer ⚠"]:::gated
    a_mw["🧩 Memory(/agents/chinook-analyst/AGENTS.md)"]
  end
  subgraph inbox["inbox-manager · haiku"]
    i_t["🔧 🔌 MCP: mock-mail · mail_create_draft ⚠"]:::gated
  end
  subgraph reviewer["quote-reviewer · sonnet-4-6"] end
  subgraph genre["genre-researcher · haiku"]
    g_t["🔧 internet_search"]
  end
  subgraph general["general-purpose (built-in, inherits main tools)"] end
```

## CLI

```
deepagents-viz <path> [-o OUTPUT] [--graph NAME]
```

- `<path>`: directory containing `langgraph.json`, a `langgraph.json` file, or a `file.py:attr` spec.
- `-o/--output`: write Mermaid to a file. **Default: stdout.**
- `--graph`: graph name when `langgraph.json` declares multiple (default: first).
- Dummy env vars are set automatically to render the maximal graph configuration.

## Testing (TDD)

- **Unit — `render/mermaid.py`**: against hand-built `AgentModel`s. Cases: single agent; agent with
  subagents (hierarchy + task edges); gated tool marker + style class; MCP existence badge; middleware
  badges incl. inferred-vs-explicit marking.
- **Unit — `model.py`**: construction and normalization of `ToolInfo`/`AgentModel`.
- **Integration — `intercept.py`**: run interception against a small fixture deep agent in
  `tests/fixtures/` that exercises `subagents`, `interrupt_on`, and a stubbed MCP client; assert the
  resulting `AgentModel`. `deepagents` is a dev dependency in the venv.

## Out of scope (v1)

- Graphviz and Excalidraw renderers (the `AgentModel` boundary makes these cheap to add later).
- Resolving individual MCP tool names (MCP shown as existence badge only).
- Subagents built via nested `create_deep_agent` calls (DeepAgents uses dicts).
- Rendering Mermaid to PNG/SVG images.

## Decisions

- **Extraction:** runtime interception + stubbing (chosen over static AST and hybrid).
- **Output format:** Mermaid (chosen over graphviz/excalidraw/multi-format for v1).
- **Scope:** subagent hierarchy + tools per agent + HITL gates + middleware badges (all four).
- **Default output:** stdout.
- **Env handling:** dummy vars set automatically for the maximal graph.
