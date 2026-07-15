# deepagents-viz

Render a [LangChain DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview.md)
agent's architecture — subagent hierarchy, tools per agent, HITL gates, and middleware —
as a Mermaid diagram. Extraction is **offline**: no LLM keys, no live services.

## How it works

`deepagents-viz` monkeypatches `create_deep_agent` so that calling it **records the resolved
arguments and returns a lightweight stand-in — the real agent graph is never compiled.** It
then imports your agent module (running any async factory) to trigger that call. Dummy env
vars and a stubbed MCP client keep the import offline. MCP servers are shown as an existence
badge only.

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
