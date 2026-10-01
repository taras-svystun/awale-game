"""The rules of Awalé. No UI and no AI here, only the game itself.

The board is stored as 12 numbers in sowing order (counter-clockwise):
index 0-5 are South's pits 1-6, index 6-11 are North's pits 1-6.
Each player counts pits from their own left, so sowing always goes
from your pit 1 to your pit 6, then on to the opponent's pit 1.
"""

from dataclasses import dataclass
from enum import Enum

PITS_PER_ROW = 6
START_SEEDS = 4
WINNING_STORE = 25


class Side(Enum):
    SOUTH = 0
    NORTH = 1

    @property
    def opponent(self) -> "Side":
        return Side.NORTH if self is Side.SOUTH else Side.SOUTH

    @property
    def first_index(self) -> int:
        return self.value * PITS_PER_ROW


@dataclass(frozen=True)
class Position:
    """The board, both stores, and whose turn it is. Never changes after it is made."""

    board: tuple[int, ...]
    stores: tuple[int, int]
    to_move: Side

    @classmethod
    def start(cls, first: Side = Side.SOUTH) -> "Position":
        return cls((START_SEEDS,) * 2 * PITS_PER_ROW, (0, 0), first)

    @classmethod
    def setup(
        cls,
        south: tuple[int, ...],
        north: tuple[int, ...],
        to_move: Side = Side.SOUTH,
        stores: tuple[int, int] = (0, 0),
    ) -> "Position":
        """Make any position by hand. Pits are listed from each owner's own left."""
        return cls(tuple(south) + tuple(north), stores, to_move)

    def pits(self, side: Side) -> tuple[int, ...]:
        i = side.first_index
        return self.board[i : i + PITS_PER_ROW]

    def store(self, side: Side) -> int:
        return self.stores[side.value]

    def legal_moves(self) -> list[int]:
        """Pits (1-6) the player to move may sow from. Empty if they cannot move at all."""
        moves = [pit for pit, seeds in enumerate(self.pits(self.to_move), start=1) if seeds > 0]
        if sum(self.pits(self.to_move.opponent)) == 0:
            # Feeding: the opponent has no seeds, so the move must reach their row.
            # From pit p, there are 6 - p pits left in our own row.
            moves = [pit for pit in moves if self.pits(self.to_move)[pit - 1] > PITS_PER_ROW - pit]
        return moves

    def play(self, pit: int) -> "Position":
        """Return the position after the player to move sows from `pit` (1-6, from their left)."""
        if pit not in self.legal_moves():
            raise ValueError(f"{self.to_move.name} cannot play pit {pit}, legal moves: {self.legal_moves()}")
        board = list(self.board)
        start = self.to_move.first_index + pit - 1
        seeds, board[start] = board[start], 0
        i = start
        while seeds:
            i = (i + 1) % len(board)
            if i == start:
                continue  # never sow back into the pit we took the seeds from
            board[i] += 1
            seeds -= 1

        # Capture: walk back from the last pit while it is the opponent's and holds 2 or 3.
        # Work on a copy, because a grand slam cancels the whole capture.
        captured_board = board.copy()
        captured = 0
        while self._is_opponents_pit(i) and captured_board[i] in (2, 3):
            captured += captured_board[i]
            captured_board[i] = 0
            i -= 1

        stores = list(self.stores)
        opponent_row = self.to_move.opponent.first_index
        is_grand_slam = sum(captured_board[opponent_row : opponent_row + PITS_PER_ROW]) == 0
        if captured and not is_grand_slam:
            board = captured_board
            stores[self.to_move.value] += captured
        return Position(tuple(board), (stores[0], stores[1]), self.to_move.opponent)

    def ends_game(self) -> bool:
        """True if the game ends here: a store has 25 seeds, or the player to move has no legal move.

        A repetition also ends a game, but a Position does not know the earlier positions, so only Game checks that.
        """
        return max(self.stores) >= WINNING_STORE or not self.legal_moves()

    def with_rows_collected(self) -> "Position":
        """Each player moves the seeds left in their own row to their store. Used when the game ends."""
        south, north = sum(self.pits(Side.SOUTH)), sum(self.pits(Side.NORTH))
        empty = (0,) * 2 * PITS_PER_ROW
        return Position(empty, (self.stores[0] + south, self.stores[1] + north), self.to_move)

    def _is_opponents_pit(self, index: int) -> bool:
        return index // PITS_PER_ROW == self.to_move.opponent.value


@dataclass(frozen=True)
class Result:
    winner: Side | None  # None means a draw
    score: tuple[int, int]  # (South, North)


class Game:
    """A whole game: every position from the start, the moves, and how it ended."""

    def __init__(self, first: Side = Side.SOUTH, start: Position | None = None):
        self._positions = [start or Position.start(first)]
        self.moves: list[int] = []
        # One flag per position: True if the game ended there.
        self._ended = [False]

    @property
    def position(self) -> Position:
        return self._positions[-1]

    @property
    def positions(self) -> tuple[Position, ...]:
        """Every position so far, from the start to now. `positions[k]` is the position after k moves."""
        return tuple(self._positions)

    @property
    def is_over(self) -> bool:
        return self.result is not None

    @property
    def result(self) -> Result | None:
        if not self._ended[-1]:
            return None
        south, north = self.position.stores
        winner = Side.SOUTH if south > north else Side.NORTH if north > south else None
        return Result(winner, (south, north))

    def play(self, pit: int) -> None:
        if self.is_over:
            raise ValueError("The game is over")
        position = self.position.play(pit)
        # A full Position includes the stores, so a match here also means nothing was captured since.
        repeated = position in self._positions
        ended = position.ends_game() or repeated
        if ended:
            # However the game ends, the seeds left on the board go to the owner of each row.
            position = position.with_rows_collected()
        self._positions.append(position)
        self._ended.append(ended)
        self.moves.append(pit)

    def copy(self) -> "Game":
        """The same game as a new object: moves and undos in one do not change the other."""
        game = Game(start=self._positions[0])
        game._positions, game._ended, game.moves = list(self._positions), list(self._ended), list(self.moves)
        return game

    def undo(self) -> None:
        """Take back the last move."""
        if not self.moves:
            raise ValueError("There is no move to undo")
        self._positions.pop()
        self._ended.pop()
        self.moves.pop()
