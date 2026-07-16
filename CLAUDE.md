# deepagents-viz — project notes

## External test agent: lca-deepagents m5/sales_assistant

`langchain-ai/lca-deepagents` (`python/m5/sales_assistant`) is a good real-world
agent for exercising the tool end to end. Clone it anywhere, then run the tool from
inside that agent's own uv environment, overlaying this checkout as an editable
dependency:

    cd <lca-deepagents>/python/m5/sales_assistant
    uv sync   # first time only
    uv run --with-editable <path-to-this-repo> deepagents-viz . -o sales_assistant.mmd

Concrete local paths for this machine live in `CLAUDE.local.md` (untracked).

## Rendering diagrams locally

`mermaid-cli` can render a `.mmd` to PNG offline using the system Chrome — useful for
verifying layout changes directly:

    # pc.json: {"args":["--no-sandbox"],"executablePath":"/usr/bin/google-chrome"}
    PUPPETEER_SKIP_DOWNLOAD=1 npx --yes @mermaid-js/mermaid-cli@latest \
        -i in.mmd -o out.png -p pc.json --backgroundColor white
