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
