# deepagents-viz

Render a [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview)
agent's architecture — subagent hierarchy, tools per agent, HITL gates, and middleware —
as a Mermaid diagram. Extraction is **offline**: no LLM keys, no live services.

## Example

Point it at a real DeepAgents project — here the
[`m5/sales_assistant`](https://github.com/langchain-ai/lca-deepagents/tree/main/python/m5/sales_assistant)
agent from `langchain-ai/lca-deepagents` — and it maps the whole hierarchy: the main agent,
each subagent it can dispatch (`sub-agent (task)` edges), and every agent's model, middleware
(`📦` marks DeepAgents' bundled defaults), tools, and HITL gates (red `⚠`). See
[`examples.md`](examples.md) for the full walkthrough and a legend.

```mermaid
%%{init: {'flowchart': {'subGraphTitleMargin': {'top': 6, 'bottom': 16}, 'padding': 4}}}%%
graph TD
  classDef mwBox fill:#fff2cc,stroke:#d6b656,stroke-width:3px,color:#1a1a1a;
  classDef toolBox fill:#d5e8d4,stroke:#82b366,stroke-width:3px,color:#1a1a1a;
  subgraph chinook_sales_assistant["chinook-sales-assistant<br/>🧠 claude-sonnet-4-6"]
    chinook_sales_assistant_mw["<div style='text-align:left'>🧩 <b>Middleware</b><br/>📦 Planning<br/>📦 Filesystem<br/>📦 SubAgent<br/>📦 Skills<br/>📦 Memory<br/>CodeInterpreter</div>"]:::mwBox
    chinook_sales_assistant_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>markdown_to_html<br/>render_pie_chart<br/>🔌 mock-mail (MCP)<br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep<br/>📦 task</div>"]:::toolBox
  end
  chinook_sales_assistant -->|"sub-agent (task)"| chinook_analyst
  subgraph chinook_analyst["chinook-analyst<br/>🧠 claude-haiku-4-5"]
    chinook_analyst_mw["<div style='text-align:left'>🧩 <b>Middleware</b><br/>📦 Planning<br/>📦 Filesystem<br/>📦 HITL<br/>Memory</div>"]:::mwBox
    chinook_analyst_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>query_chinook<br/>introspect_schema<br/><span style='color:#c00'>⚠</span> add_customer (HITL)<br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep</div>"]:::toolBox
  end
  chinook_sales_assistant -->|"sub-agent (task)"| quote_reviewer
  subgraph quote_reviewer["quote-reviewer<br/>🧠 claude-sonnet-4-6"]
    quote_reviewer_mw["<div style='text-align:left'>🧩 <b>Middleware</b><br/>📦 Planning<br/>📦 Filesystem</div>"]:::mwBox
    quote_reviewer_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep</div>"]:::toolBox
  end
  chinook_sales_assistant -->|"sub-agent (task)"| inbox_manager
  subgraph inbox_manager["inbox-manager<br/>🧠 claude-haiku-4-5"]
    inbox_manager_mw["<div style='text-align:left'>🧩 <b>Middleware</b><br/>📦 Planning<br/>📦 Filesystem<br/>📦 HITL</div>"]:::mwBox
    inbox_manager_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>🔌 mock-mail (MCP)<br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep<br/><span style='color:#c00'>⚠</span> mail_create_draft (HITL)</div>"]:::toolBox
  end
  chinook_sales_assistant -->|"sub-agent (task)"| genre_researcher
  subgraph genre_researcher["genre-researcher<br/>🧠 claude-haiku-4-5"]
    genre_researcher_mw["<div style='text-align:left'>🧩 <b>Middleware</b><br/>📦 Planning<br/>📦 Filesystem</div>"]:::mwBox
    genre_researcher_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>internet_search<br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep</div>"]:::toolBox
  end
  chinook_sales_assistant -->|"sub-agent (task)"| general_purpose
  subgraph general_purpose["📦 general-purpose<br/>🧠 claude-sonnet-4-6"]
    general_purpose_t["<div style='text-align:left'>🔧 <b>Tools</b><br/>markdown_to_html<br/>render_pie_chart<br/>🔌 mock-mail (MCP)<br/>📦 write_todos<br/>📦 ls<br/>📦 read_file<br/>📦 write_file<br/>📦 edit_file<br/>📦 glob<br/>📦 grep</div>"]:::toolBox
  end
  style chinook_sales_assistant fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
  style chinook_analyst fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
  style quote_reviewer fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
  style inbox_manager fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
  style genre_researcher fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
  style general_purpose fill:#dae8fc,stroke:#6c8ebf,stroke-width:3px,color:#1a1a1a;
```

## How it works

`deepagents-viz` monkeypatches `create_deep_agent` so that calling it **records the resolved
arguments and returns a lightweight stand-in — the real agent graph is never compiled.** It
then imports your agent module (calling any factory function, sync or async) to trigger that
call. Dummy env vars and a stubbed MCP client keep the import offline. MCP servers are shown
as an existence badge only.

## Install & run

Once published to PyPI, run it **inside your agent's own environment** (where `deepagents`
and the agent's other dependencies are installed):

```bash
uv run --with deepagents-viz deepagents-viz path/to/agent_dir            # print Mermaid
uv run --with deepagents-viz deepagents-viz path/to/agent_dir -o out.mmd # write a file
uv run --with deepagents-viz deepagents-viz ./agent.py:make_graph        # target a factory
uv run --with deepagents-viz deepagents-viz . --graph agent              # pick a graph
```

`target` may be: a directory containing `langgraph.json`, a `langgraph.json` path, or a
`file.py:attr` spec.

### Running locally (before it's on PyPI)

**Against the bundled test fixtures**, from this repository — `uv run` installs this project
into its own environment, and the fixtures only need `deepagents` (a dev dependency):

```bash
uv run deepagents-viz tests/fixtures/simple              # print Mermaid
uv run deepagents-viz tests/fixtures/factory -o out.mmd  # write a file
# or, without the console script:
uv run python -m deepagents_viz.cli tests/fixtures/simple
```

**Against an agent in another directory**, the tool must run in *that* agent's environment
so all of the agent's own dependencies import. Overlay this checkout onto it with a local
path instead of a package name:

```bash
cd /path/to/other-agent   # a uv project with its own deps + deepagents installed
uv run --with-editable /path/to/deepagents-viz deepagents-viz m5/sales_assistant -o out.mmd
```

The rule either way: **the target's full dependency set must be importable in whatever
environment runs the tool** — which is why an external agent uses its own env plus
`--with-editable`, not this repo's environment.

## Examples

See [`examples.md`](examples.md) for worked, end-to-end walkthroughs: the two bundled test
fixtures (with their commands and rendered Mermaid output) and a full setup for pointing
the tool at an external agent, `m5/sales_assistant`.

## Viewing the diagram

- Paste the output into <https://mermaid.live> (Export → PNG/SVG), or
- drop it in a ```` ```mermaid ```` fenced block in a Markdown file on GitHub.

## Development

```bash
uv sync                        # install dev dependencies (pytest, ruff, pre-commit)
uv run pre-commit install      # enable the git pre-commit hook (once per clone)
uv run pytest                  # run the test suite
uv run ruff check .            # lint
uv run ruff format .           # auto-format
```

The pre-commit hook runs Ruff (lint + format) on staged files. The same checks, plus the
test suite across Python 3.11–3.13, run in CI on every pull request and on pushes to `main`.

## Limitations

- Individual MCP tool names are not resolved (existence badge per server).
- The DeepAgents-bundled middleware and built-in tools (marked with a `📦` prefix — e.g.
  `Planning`, `Filesystem`, `SubAgent`, and their tools) are inferred from the call's
  configuration rather than read back from the composed middleware/tool list.
- Subagents built via nested `create_deep_agent` calls are not modelled (DeepAgents
  uses dicts).

## Roadmap

- Graphviz/DOT renderer for offline PNG/SVG from Python (via the native `dot` binary).
