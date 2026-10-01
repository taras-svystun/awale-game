"""What every AI agent looks like from the outside."""

import random
from abc import ABC
from dataclasses import dataclass, field

from awale.engine import Position


@dataclass(frozen=True)
class Thoughts:
    """What an agent shows about how it chose its move. Watch draws these next to the board.

    Only `move` is needed. An agent that does not look ahead (like Random) leaves the rest empty.
    """

    move: int  # the pit it chose, 1-6 from the mover's own left
    # The score of each legal move, for the player to move: higher is better.
    scores: dict[int, float] = field(default_factory=dict)
    # The moves it expects next, starting with `move`, then the opponent's answer, and so on.
    line: tuple[int, ...] = ()
    positions: int = 0  # how many positions it looked at
    depth: int = 0  # how many moves ahead it looked
    # Moves whose score is only an upper bound: the move is worth this score or less.
    # Alpha-beta can prove that a move is worse than the best one without finding its exact score.
    upper_bounds: frozenset[int] = frozenset()
    # How many random games it played to the end, for an agent that judges moves that way (MCTS).
    playouts: int = 0


class Agent(ABC):
    """Chooses a move in a position.

    Write one of the two methods:
    - `choose_move`, for an agent with nothing to show, like Random;
    - `think`, for an agent that can show its thoughts (move scores, the line it expects, the work it did).
    Each one is built from the other, so the window, Watch and Tournament can call either
    and any agent can play against any other.
    """

    name = "Agent"

    def __init__(self, seed: int | None = None):
        # Every agent has its own random generator, for agents that use chance (Random, Greedy's ties, MCTS).
        # Not the shared `random` module: the same seed then always gives the same moves,
        # so a game or a whole tournament can be repeated exactly.
        self.rng = random.Random(seed)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Each method calls the other, so an agent that writes neither would loop forever. Stop it early.
        if cls.choose_move is Agent.choose_move and cls.think is Agent.think:
            raise TypeError(f"{cls.__name__} must define choose_move or think")

    def choose_move(self, position: Position) -> int:
        """Return one of `position.legal_moves()`: a pit 1-6, from the mover's own left.

        It is only called when the player to move has a legal move.
        It may run in a background thread, so it must not touch the window.
        """
        return self.think(position).move

    def think(self, position: Position) -> Thoughts:
        """Choose a move, like `choose_move`, and also say how it was chosen."""
        return Thoughts(self.choose_move(position))
