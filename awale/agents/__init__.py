"""Agents: anything that chooses a move in a position. No Pygame here."""

from awale.agents.base import Agent, Thoughts
from awale.agents.greedy_agent import GreedyAgent
from awale.agents.minimax_agent import MinimaxAgent
from awale.agents.random_agent import RandomAgent

# Every AI agent you can pick in the start menu, by the name shown there.
AGENTS: dict[str, type[Agent]] = {
    "Random": RandomAgent,
    "Greedy": GreedyAgent,
    "Minimax": MinimaxAgent,
}
# Agents that look a fixed number of moves ahead. Their name may end with ":depth", like "Minimax:6".
SEARCH_AGENTS = {"Minimax"}


def make_agent(name: str, seed: int | None = None) -> Agent:
    """Build an agent from its name: a key of AGENTS, like "Greedy",
    or a search agent with its depth, like "Minimax:6". Raises ValueError for a name it does not know.
    """
    base, has_depth, depth = name.partition(":")
    if base not in AGENTS:
        raise ValueError(f"No agent called {base!r}. The agents are: {', '.join(AGENTS)}")
    if not has_depth:
        agent = AGENTS[base](seed=seed)
    elif base not in SEARCH_AGENTS:
        raise ValueError(f"{base} has no depth to set. Only these do: {', '.join(sorted(SEARCH_AGENTS))}")
    elif not depth.isdigit() or int(depth) < 1:
        raise ValueError(f"The depth in {name!r} must be a whole number from 1 up")
    else:
        agent = AGENTS[base](seed=seed, depth=int(depth))
    # Shown in the window and written in game records, so "Minimax:6" is not mistaken for the default depth.
    agent.name = name
    return agent


__all__ = ["AGENTS", "SEARCH_AGENTS", "Agent", "GreedyAgent", "MinimaxAgent", "RandomAgent", "Thoughts", "make_agent"]
