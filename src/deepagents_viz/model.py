from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ToolInfo:
    name: str
    kind: Literal["function", "mcp", "builtin"] = "function"
    gated: bool = False
    mcp_server: str | None = None


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
    subagents: list[AgentModel] = field(default_factory=list)
    is_builtin: bool = False
