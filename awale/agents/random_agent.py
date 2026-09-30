"""The Random agent: the simplest agent, and the baseline every other agent must beat."""

from awale.agents.base import Agent
from awale.engine import Position


class RandomAgent(Agent):
    """Plays any legal move, each with the same chance."""

    name = "Random"

    def choose_move(self, position: Position) -> int:
        # self.rng comes from Agent, and is seeded by `RandomAgent(seed=...)`.
        # No thinking at all: every legal move has the same chance.
        return self.rng.choice(position.legal_moves())
