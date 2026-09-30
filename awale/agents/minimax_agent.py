"""The Minimax agent: looks several moves ahead, and expects the opponent to answer with their best move."""

from collections.abc import Callable

from awale.agents.base import Agent, Thoughts
from awale.agents.heuristics import store_diff
from awale.engine import Position, Side

DEPTH = 4
# A won game is worth more than any heuristic score: store_diff is never more than 48.
WIN = 100


class MinimaxAgent(Agent):
    """Tries every line of play `depth` moves deep. On its own turns it takes the best move for itself,
    on the opponent's turns it expects the worst move for itself. The heuristic judges where the lines stop.
    """

    name = "Minimax"

    def __init__(
        self,
        seed: int | None = None,
        depth: int = DEPTH,
        heuristic: Callable[[Position, Side], float] = store_diff,
    ):
        super().__init__(seed)
        if depth < 1:
            raise ValueError(f"{self.name} needs a depth of at least 1, not {depth}")
        self.depth = depth
        self.heuristic = heuristic
        self.positions = 0  # counted by the search, and reset for each move

    def think(self, position: Position) -> Thoughts:
        me = position.to_move
        self.positions = 0
        # The value of each legal move for us, and the line of play we expect after it.
        results = {pit: self.minimax(position.play(pit), self.depth - 1, me) for pit in position.legal_moves()}
        self.positions += len(results)
        scores = {pit: value for pit, (value, _) in results.items()}
        best = max(scores.values())
        # Like Greedy: when several moves are equally good, there is no reason to prefer the leftmost one.
        move = self.rng.choice([pit for pit, score in scores.items() if score == best])
        line = (move, *results[move][1])
        return Thoughts(move, scores, line, self.positions, self.depth)

    def minimax(self, position: Position, depth: int, me: Side) -> tuple[float, tuple[int, ...]]:
        """How good `position` is for `me`, looking `depth` more moves ahead.

        Returns the value, and the line of play from here that leads to it.
        """
        if position.ends_game():
            return self.final_value(position, me, depth), ()
        if depth == 0:
            return self.heuristic(position, me), ()
        results = []
        for pit in position.legal_moves():
            value, line = self.minimax(position.play(pit), depth - 1, me)
            results.append((value, (pit, *line)))
        self.positions += len(results)
        # Our turn: we take our best move. The opponent's turn: we expect their best move, which is our worst.
        # On a tie both take the first one, the leftmost pit.
        best = max if position.to_move is me else min
        return best(results, key=lambda result: result[0])

    @staticmethod
    def final_value(position: Position, me: Side, depth: int) -> float:
        """The value of a position where the game ends: a win, a loss or a draw, not a guess.

        `depth` is how many moves the search could still look ahead. A win found earlier keeps
        more of it, so a quick win scores higher than a slow one, and a slow loss higher than a quick one.
        """
        final = position.with_rows_collected()  # the seeds left on the board go to each row's owner
        difference = final.store(me) - final.store(me.opponent)
        if difference > 0:
            return WIN + depth
        if difference < 0:
            return -WIN - depth
        return 0
