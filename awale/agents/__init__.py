"""Agents: anything that chooses a move in a position. No Pygame here."""

from awale.agents.alphabeta_agent import AlphaBetaAgent
from awale.agents.base import Agent, Thoughts
from awale.agents.greedy_agent import GreedyAgent
from awale.agents.heuristics import HEURISTICS
from awale.agents.minimax_agent import MinimaxAgent
from awale.agents.random_agent import RandomAgent

# Every AI agent you can pick in the start menu, by the name shown there.
AGENTS: dict[str, type[Agent]] = {
    "Random": RandomAgent,
    "Greedy": GreedyAgent,
    "Minimax": MinimaxAgent,
    "AlphaBeta": AlphaBetaAgent,
}
# Agents that look a fixed number of moves ahead. Their name may add a depth and a heuristic
# after colons, in any order: "Minimax:6", "AlphaBeta:mix", "AlphaBeta:8:mix".
SEARCH_AGENTS = {"Minimax", "AlphaBeta"}


def make_agent(name: str, seed: int | None = None) -> Agent:
    """Build an agent from its name: a key of AGENTS, like "Greedy",
    or a search agent with a depth and/or a heuristic, like "Minimax:6" or "AlphaBeta:8:mix".
    Raises ValueError for a name it does not know.
    """
    base, *options = name.split(":")
    if base not in AGENTS:
        raise ValueError(f"No agent called {base!r}. The agents are: {', '.join(AGENTS)}")
    if options and base not in SEARCH_AGENTS:
        raise ValueError(f"{base} has no depth or heuristic to set. Only these do: {', '.join(sorted(SEARCH_AGENTS))}")
    settings = {}
    for option in options:
        if option.isdigit() and int(option) >= 1:
            key, value = "depth", int(option)
        elif option in HEURISTICS:
            key, value = "heuristic", HEURISTICS[option]
        else:
            raise ValueError(
                f"{option!r} in {name!r} is neither a depth (a whole number from 1 up) "
                f"nor a heuristic ({', '.join(HEURISTICS)})"
            )
        if key in settings:
            raise ValueError(f"{name!r} sets the {key} twice")
        settings[key] = value
    agent = AGENTS[base](seed=seed, **settings)
    # Shown in the window and written in game records, so "Minimax:6" is not mistaken for the default depth.
    agent.name = name
    return agent

__all__ = [
    "AGENTS",
    "HEURISTICS",
    "SEARCH_AGENTS",
    "Agent",
    "AlphaBetaAgent",
    "GreedyAgent",
    "MinimaxAgent",
    "RandomAgent",
    "Thoughts",
    "make_agent",
]
