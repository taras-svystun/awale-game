"""What every AI agent looks like from the outside."""

import random
from abc import ABC, abstractmethod

from awale.engine import Position


class Agent(ABC):
    """Chooses a move in a position.

    The window, and later Watch and Tournament, only ever call `choose_move`,
    so any agent can play against any other.
    """

    name = "Agent"

    def __init__(self, seed: int | None = None):
        # Every agent has its own random generator, for agents that use chance (Random now, MCTS later).
        # Not the shared `random` module: the same seed then always gives the same moves,
        # so a game or a whole tournament can be repeated exactly.
        self.rng = random.Random(seed)

    @abstractmethod
    def choose_move(self, position: Position) -> int:
        """Return one of `position.legal_moves()`: a pit 1-6, from the mover's own left.

        It is only called when the player to move has a legal move.
        It may run in a background thread, so it must not touch the window.
        """
