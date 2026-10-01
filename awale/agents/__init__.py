"""Agents: anything that chooses a move in a position. No Pygame here."""

import math

from awale.agents.alphabeta_agent import AlphaBetaAgent
from awale.agents.base import Agent, Thoughts
from awale.agents.deepening_agent import DeepeningAgent
from awale.agents.greedy_agent import GreedyAgent
from awale.agents.heuristics import HEURISTICS
from awale.agents.mcts_agent import MCTSAgent
from awale.agents.minimax_agent import MinimaxAgent
from awale.agents.random_agent import RandomAgent

# Every AI agent you can pick in the start menu, by the name shown there.
AGENTS: dict[str, type[Agent]] = {
    "Random": RandomAgent,
    "Greedy": GreedyAgent,
    "Minimax": MinimaxAgent,
    "AlphaBeta": AlphaBetaAgent,
    "Deepening": DeepeningAgent,
    "MCTS": MCTSAgent,
}
# What each agent can set after colons in its name, in any order: "AlphaBeta:8:mix", "Deepening:0.5s:mix", "MCTS:1000".
# A whole number is the depth, or the number of playouts for MCTS; a name is a heuristic;
# a number with an "s" is a time limit per move, in seconds. Random and Greedy have nothing to set.
OPTIONS: dict[str, tuple[str, ...]] = {
    "Minimax": ("depth", "heuristic"),
    "AlphaBeta": ("depth", "heuristic"),
    "Deepening": ("depth", "heuristic", "time_limit"),
    "MCTS": ("playouts", "time_limit"),
}
OPTION_TEXT = {
    "depth": "a depth (a whole number from 1 up)",
    "playouts": "a number of playouts (a whole number from 1 up)",
    "heuristic": f"a heuristic ({', '.join(HEURISTICS)})",
    "time_limit": "a time limit (like 0.5s)",
}


def make_agent(name: str, seed: int | None = None) -> Agent:
    """Build an agent from its name: a key of AGENTS, like "Greedy",
    maybe with options after colons (see OPTIONS), like "Minimax:6", "AlphaBeta:8:mix" or "MCTS:0.5s".
    Raises ValueError for a name it does not know.
    """
    base, *options = name.split(":")
    if base not in AGENTS:
        raise ValueError(f"No agent called {base!r}. The agents are: {', '.join(AGENTS)}")
    allowed = OPTIONS.get(base, ())
    if options and not allowed:
        raise ValueError(f"{base} has nothing to set after a colon. Only these do: {', '.join(OPTIONS)}")
    settings = {}
    for option in options:
        if option.isdigit() and int(option) >= 1:
            key, value = ("playouts" if "playouts" in allowed else "depth"), int(option)
        elif option in HEURISTICS:
            key, value = "heuristic", HEURISTICS[option]
        elif seconds(option):
            key, value = "time_limit", seconds(option)
        else:
            key = None
        if key not in allowed:
            raise ValueError(f"{option!r} in {name!r} is not {' nor '.join(OPTION_TEXT[key] for key in allowed)}")
        if key in settings:
            raise ValueError(f"{name!r} sets the {key.replace('_', ' ')} twice")
        settings[key] = value
    agent = AGENTS[base](seed=seed, **settings)
    # Shown in the window and written in game records, so "Minimax:6" is not mistaken for the default depth.
    agent.name = name
    return agent


def seconds(option: str) -> float | None:
    """The time in an option like "0.5s" or "2s", or None if the option is not a time above 0."""
    if not option.endswith("s"):
        return None
    try:
        value = float(option[:-1])
    except ValueError:
        return None
    return value if 0 < value < math.inf else None


__all__ = [
    "AGENTS",
    "HEURISTICS",
    "OPTIONS",
    "Agent",
    "AlphaBetaAgent",
    "DeepeningAgent",
    "GreedyAgent",
    "MCTSAgent",
    "MinimaxAgent",
    "RandomAgent",
    "Thoughts",
    "make_agent",
]
