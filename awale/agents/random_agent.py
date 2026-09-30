"""The Random agent: the simplest agent, and the baseline every other agent must beat."""

import random

from awale.agents.base import Agent
from awale.engine import Position


class RandomAgent(Agent):
    """Plays any legal move, each with the same chance."""

    name = "Random"

    def __init__(self, seed: int | None = None):
        # Its own random generator, not the shared `random` module:
        # the same seed then always gives the same moves, so a game can be repeated.
        self.rng = random.Random(seed)

    def choose_move(self, position: Position) -> int:
        # Taras writes this. The tests are in tests/test_random_agent.py.
        raise NotImplementedError("RandomAgent.choose_move is not written yet")
