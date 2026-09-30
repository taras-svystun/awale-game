"""What every AI agent looks like from the outside."""

from abc import ABC, abstractmethod

from awale.engine import Position


class Agent(ABC):
    """Chooses a move in a position.

    The window, and later Watch and Tournament, only ever call `choose_move`,
    so any agent can play against any other.
    """

    name = "Agent"

    @abstractmethod
    def choose_move(self, position: Position) -> int:
        """Return one of `position.legal_moves()`: a pit 1-6, from the mover's own left.

        It is only called when the player to move has a legal move.
        It may run in a background thread, so it must not touch the window.
        """
