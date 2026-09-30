"""Heuristics: functions that look at a position and say how good it is for one player.

A heuristic does not choose moves. A search (like Minimax) calls it on the positions
at the end of its look-ahead, where it stops and has to guess.

`store_diff` counts only the seeds already captured. The features below look at the board too.
Each one is "mine minus the opponent's", so it is positive when the position is good for `me`.
A feature alone is not a heuristic: `weighted` adds features to `store_diff`, each with a weight
that says how many captured seeds it is worth.
"""

from collections.abc import Callable

from awale.engine import Position, Side

Heuristic = Callable[[Position, Side], float]

# A pit with this many seeds sows all the way around the board and on into the opponent's row again.
BIG_PIT = 12


def store_diff(position: Position, me: Side) -> int:
    """My store minus the opponent's store: how many seeds I am ahead right now."""
    return position.store(me) - position.store(me.opponent)


def row_seeds(position: Position, me: Side) -> int:
    """Seeds in my row minus seeds in the opponent's row.

    Seeds in my row are mine to sow, and they are mine when the game ends.
    """
    return sum(position.pits(me)) - sum(position.pits(me.opponent))


def weak_pits(position: Position, me: Side) -> int:
    """The opponent's pits with 1 or 2 seeds, minus mine.

    One more seed makes such a pit hold 2 or 3, so it can be captured.
    """
    return _count(position.pits(me.opponent), 1, 2) - _count(position.pits(me), 1, 2)


def mobility(position: Position, me: Side) -> int:
    """My pits that are not empty, minus the opponent's: how many moves each player has to choose from."""
    return _count(position.pits(me), 1, 48) - _count(position.pits(me.opponent), 1, 48)


def big_pits(position: Position, me: Side) -> int:
    """My pits with 12 or more seeds, minus the opponent's.

    Such a pit sows at least one seed into every pit of the opponent's row, then goes on into it again.
    Pits with 1 or 2 seeds become 2 or 3, so it can capture a lot in one move.
    """
    return _count(position.pits(me), BIG_PIT, 48) - _count(position.pits(me.opponent), BIG_PIT, 48)


def _count(pits: tuple[int, ...], low: int, high: int) -> int:
    """How many of `pits` hold from `low` to `high` seeds."""
    return sum(low <= seeds <= high for seeds in pits)


def weighted(weights: dict[Callable[[Position, Side], int], float]) -> Heuristic:
    """A heuristic: `store_diff`, plus each feature times its weight.

    With `{row_seeds: 0.25}`, 4 more seeds in my row are worth as much as 1 more seed in my store.
    """

    def heuristic(position: Position, me: Side) -> float:
        value = store_diff(position, me)
        for feature, weight in weights.items():
            value += weight * feature(position, me)
        # 0.1 has no exact value in binary, so 0.1 * 3 gives 0.30000000000000004. Rounding makes two positions
        # that are worth the same get exactly the same score, so they are a real tie.
        return round(value, 6)

    heuristic.weights = weights  # so a test can check that no position looks as good as a won game
    return heuristic


# Every heuristic a search agent can use, by the name that goes after a colon: "AlphaBeta:mix".
# The weights come from tournaments against "store", see docs/agents/heuristics.md.
HEURISTICS: dict[str, Heuristic] = {
    "store": store_diff,
    # One feature each, to test it alone.
    "seeds": weighted({row_seeds: 0.1}),
    "weak": weighted({weak_pits: 0.5}),
    "mobility": weighted({mobility: 0.5}),
    "big": weighted({big_pits: 1}),
    # The best mix we found. Weak pits and big pits did not make it stronger, so they are left out.
    "mix": weighted({mobility: 0.5, row_seeds: 0.1}),
}
