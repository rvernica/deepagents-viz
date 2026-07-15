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
