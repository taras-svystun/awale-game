"""The AlphaBeta agent: chooses exactly the moves Minimax chooses, but skips the lines that cannot change them."""

import math
from collections.abc import Callable

from awale.agents.heuristics import store_diff
from awale.agents.minimax_agent import MinimaxAgent
from awale.engine import Position, Side

# Two moves deeper than Minimax: it is still quick (about 15 ms per move), and each move of depth wins clearly.
DEPTH = 6
INFINITY = math.inf


class AlphaBetaAgent(MinimaxAgent):
    """Minimax with alpha-beta pruning.

    Minimax tries every line of play to the end of its depth. But once we know one move is good enough,
    we do not need to know exactly how bad each other move is, only that it is worse. As soon as one
    answer of the opponent shows that a move is worse than one we already have, the other answers
    to that move are skipped. The values, the lines and the chosen moves are the same as Minimax's.
    """

    name = "AlphaBeta"

    def __init__(
        self,
        seed: int | None = None,
        depth: int = DEPTH,
        heuristic: Callable[[Position, Side], float] = store_diff,
    ):
        super().__init__(seed, depth, heuristic)

    def minimax(self, position: Position, depth: int, me: Side) -> tuple[float, tuple[int, ...]]:
        # Minimax's `think` calls this for each of our moves. We search each one with the widest window,
        # so every move gets its exact score, as in Minimax: Watch shows the same scores,
        # and a tie between the best moves is broken at random in the same way.
        return self.alphabeta(position, depth, me, -INFINITY, INFINITY)

    def alphabeta(
        self, position: Position, depth: int, me: Side, alpha: float, beta: float
    ) -> tuple[float, tuple[int, ...]]:
        """How good `position` is for `me`, looking `depth` more moves ahead, like `minimax`.

        `alpha` is a value `me` can already get somewhere higher in the tree, and `beta` a value the
        opponent can already hold us to. The game never reaches this position if it is worth alpha or less
        (we would play the other way), or beta or more (the opponent would). So:
        - if the value is between alpha and beta, it is exact, and so is the line;
        - if it is alpha or less, we only learn "alpha or less", and the same for beta or more.
        That is all the positions above need, and it lets us stop early.
        """
        if position.ends_game():
            return self.final_value(position, me, depth), ()
        if depth == 0:
            return self.heuristic(position, me), ()
        our_turn = position.to_move is me
        best, best_line = (-INFINITY if our_turn else INFINITY), ()
        for pit in position.legal_moves():
            self.positions += 1
            value, line = self.alphabeta(position.play(pit), depth - 1, me, alpha, beta)
            # Only a strictly better value replaces the best, so on a tie we keep the leftmost pit, like Minimax.
            if our_turn:
                if value > best:
                    best, best_line = value, (pit, *line)
                alpha = max(alpha, best)
            else:
                if value < best:
                    best, best_line = value, (pit, *line)
                beta = min(beta, best)
            if alpha >= beta:
                # Our turn: we already have a move worth beta or more, and the opponent will not allow it.
                # Their turn: they already have an answer worth alpha or less to us, and we will not allow it.
                # Either way the game never comes here, so the other moves do not matter.
                break
        return best, best_line
