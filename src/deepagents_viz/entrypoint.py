from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

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
    if not isinstance(spec, str) or ":" not in spec:
        raise RuntimeError(f"Graph spec {spec!r} in {json_path} is not in 'path:attr' form.")
    rel_path, attr = spec.rsplit(":", 1)
    base = json_path.parent
    module_file = (base / rel_path).resolve()
    if not module_file.is_file():
        raise RuntimeError(
            f"Graph module {module_file} (from spec {spec!r}) does not exist. "
            f"Module-style specs like 'pkg.mod:graph' are not supported; use a file path."
        )

    syspath_dirs = [module_file.parent]
    for dep in data.get("dependencies", []) or []:
        dep_dir = (base / dep).resolve()
        if dep_dir.is_dir() and dep_dir not in syspath_dirs:
            syspath_dirs.append(dep_dir)
    return Target(module_file, attr, syspath_dirs, graph_name)


def parse_target(target: str, graph: str | None = None) -> Target:
    if ":" in target and target.rsplit(":", 1)[0].endswith(".py"):
        path_part, attr = target.rsplit(":", 1)
        module_file = Path(path_part).resolve()
        if not module_file.is_file():
            raise RuntimeError(f"Target module {module_file} (from {target!r}) does not exist.")
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


def _import_module(module_file: Path, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_agent_model(target: str, graph: str | None = None) -> AgentModel:
    t = parse_target(target, graph)

    saved_sys_path = list(sys.path)
    mod_name = None
    try:
        digest = hashlib.md5(str(t.module_file).encode(), usedforsecurity=False).hexdigest()[:12]
        mod_name = f"_deepagents_viz_target_{digest}"

        intercept.set_dummy_env()
        intercept.install_create_deep_agent_patch()
        intercept.install_mcp_stub()
        intercept.reset()

        for d in reversed(t.syspath_dirs):
            sys.path.insert(0, str(d))
        module = _import_module(t.module_file, mod_name)

        if not hasattr(module, t.attr):
            raise RuntimeError(f"Attribute {t.attr!r} not found in module {t.module_file}")
        attr = getattr(module, t.attr)

        # Resolve the agent object for the selected attribute. A module-level
        # agent is the recorder's (tagged) MagicMock; a factory is called to
        # produce one. Each recorded call tags its MagicMock with the index of
        # its entry in CAPTURED, so we render the SELECTED graph rather than
        # merely the last create_deep_agent call the import happened to run.
        if inspect.iscoroutinefunction(attr):
            agent_obj = asyncio.run(attr())
        elif callable(attr) and not isinstance(attr, MagicMock):
            agent_obj = attr()
            if inspect.iscoroutine(agent_obj):
                agent_obj = asyncio.run(agent_obj)
        else:
            agent_obj = attr

        if not intercept.CAPTURED:
            raise RuntimeError(
                f"No create_deep_agent(...) call was captured for target {target!r}."
            )

        index = getattr(agent_obj, "_deepagents_viz_index", None)
        if not isinstance(index, int) or not (0 <= index < len(intercept.CAPTURED)):
            index = len(intercept.CAPTURED) - 1
        return build_model_from_kwargs(intercept.CAPTURED[index], default_name=t.graph_name)
    finally:
        sys.path[:] = saved_sys_path
        if mod_name is not None:
            sys.modules.pop(mod_name, None)
        intercept.uninstall_create_deep_agent_patch()
        intercept.uninstall_mcp_stub()
