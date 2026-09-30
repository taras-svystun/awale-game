"""Heuristics: functions that look at a position and say how good it is for one player.

A heuristic does not choose moves. A search (like Minimax) calls it on the positions
at the end of its look-ahead, where it stops and has to guess.
"""

from awale.engine import Position, Side


def store_diff(position: Position, me: Side) -> int:
    """My store minus the opponent's store: how many seeds I am ahead right now."""
    return position.store(me) - position.store(me.opponent)
