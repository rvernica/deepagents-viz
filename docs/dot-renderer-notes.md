# DOT / Graphviz renderer — design notes

Notes captured while doing the Mermaid graphics work, for when the roadmap's
"Graphviz/DOT renderer for offline PNG/SVG from Python (via the native `dot` binary)"
item is picked up.

## Decision

Go with **two hand-written renderers sharing a style module** (option #1 below).
Code is left as-is for now (`render/mermaid.py` stays self-contained); the shared
`style.py` extraction happens when the DOT work actually starts.

## What carries over vs. what doesn't

- **Carries over completely (renderer-agnostic):** the whole extraction layer and the
  `AgentModel` / `ToolInfo` / `MiddlewareInfo` model — including the `bundled`, `gated`,
  `kind`, `mcp_server` flags and the general-purpose-tool logic. `render/mermaid.py` is a
  pure `model → string` function; a DOT renderer is a *second* such function over the
  same model. None of the semantic work is Mermaid-specific.
- **Does NOT carry over:** every line of Mermaid *syntax* — `subgraph` / `classDef` /
  `style` / `:::` / `-->|…|`, the `<br/>`, `<div>`, `<span>`, and the `%%{init …}%%`
  directive. All string formatting, rewritten in DOT's grammar.

## Feature-by-feature mapping to DOT

| Customization                         | DOT equivalent                                              | Notes |
|---------------------------------------|------------------------------------------------------------|-------|
| Box-in-box (agent → mw/tool)          | nested `subgraph cluster_*`                                 | Native. |
| Pastel fills + thick darker borders   | `style=filled fillcolor="#dae8fc" color="#6c8ebf" penwidth=3` | Direct. |
| Bold titles, colored `⚠`, multi-line  | HTML-like labels `label=<…<b>…</b>…<font color="red">⚠</font>…>` | Well-supported. |
| Left-align + top-left title           | `<td align="left">` / cluster `labeljust=l labelloc=t`     | **Easier than Mermaid** — no padding/width hacks. |
| Edge label `sub-agent (task)`         | `[label="sub-agent (task)"]`                               | Trivial. |
| `subGraphTitleMargin`, `padding:4`    | —                                                          | **Not needed** — Mermaid-only workarounds; Graphviz lays this out natively. |
| Emoji (🧩 🔧 🔌 📦 🧠 ⚠)               | depends on font                                            | **The one real risk** — see below. |

## The emoji caveat

Mermaid renders in a browser, so emoji "just work" via system fonts. Graphviz renders
with whatever font it's given; with a default font, emoji come out as tofu boxes.
Fixable — install an emoji font and set `fontname="Noto Color Emoji"` (or supply a
fontconfig) — but it's real setup work and a portability concern. Verify on target
systems, and consider a monochrome-glyph or plain-text fallback.

## Alternatives considered (really a "why DOT?" question)

1. **Two hand-written renderers sharing a style module — CHOSEN.** Factor the
   palette/emoji/label constants (`AGENT_FILL`, `BUNDLED`, the emoji, `(HITL)`/`(MCP)`
   suffixes) out of `mermaid.py` into a shared `style.py`; both `mermaid.py` and a new
   `dot.py` consume it. Keeps visual identity consistent, avoids drift. DOT's HTML
   tables make our layout intentions cleaner.
2. **Skip DOT; get offline PNG/SVG via `mermaid-cli`.** Headless Chrome + `mmdc` gives
   offline raster with pixel-identical fidelity and zero re-implementation. Cost: a
   Node + Chromium dependency, heavier than a native `dot` binary (presumably why the
   roadmap specified DOT). If the goal is "offline images without a browser," DOT wins;
   if it's "offline images at all," mermaid-cli already delivers with full fidelity.
3. **A shared visual-IR both backends emit from.** Over-engineered for two targets —
   `AgentModel` already serves this role. Skip.

## Local rendering during development

`mermaid-cli` can render `.mmd` → PNG offline using the system Chrome, useful for
verifying layout changes directly:

```bash
# puppeteer config (pc.json): {"args":["--no-sandbox"],"executablePath":"/usr/bin/google-chrome"}
PUPPETEER_SKIP_DOWNLOAD=1 npx --yes @mermaid-js/mermaid-cli@latest -i in.mmd -o out.png -p pc.json --backgroundColor white
```
