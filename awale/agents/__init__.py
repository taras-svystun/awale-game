"""Agents: anything that chooses a move in a position. No Pygame here."""

from awale.agents.base import Agent, Thoughts
from awale.agents.random_agent import RandomAgent

# Every AI agent you can pick in the start menu, by the name shown there.
AGENTS: dict[str, type[Agent]] = {
    "Random": RandomAgent,
}

__all__ = ["AGENTS", "Agent", "RandomAgent", "Thoughts"]
