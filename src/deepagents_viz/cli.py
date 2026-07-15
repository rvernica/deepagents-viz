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
