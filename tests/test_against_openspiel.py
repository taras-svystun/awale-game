"""Play thousands of random games in our engine and in OpenSpiel at the same time.

OpenSpiel's `oware` uses the same rules as we do (see docs/adr/0001), so after every
move both engines must show the same board, stores, player to move and legal moves.
"""

import random

import pyspiel
import pytest

from awale.engine import Game, Side

GAMES = 2000
# OpenSpiel stops with an error at 1000 moves. Random games almost never get that long.
OPENSPIEL_MAX_MOVES = 999


def openspiel_view(state) -> tuple:
    """Read OpenSpiel's board. Its text looks like "0 | 3 5 | 1 6 5 ..." (player | stores | 12 pits)."""
    _player, stores, board = state.observation_string(0).split(" | ")
    return tuple(map(int, board.split())), tuple(map(int, stores.split()))


@pytest.mark.parametrize("seed", range(GAMES))
def test_random_game_matches_openspiel(seed):
    rng = random.Random(seed)
    ours = Game(first=Side.SOUTH)
    theirs = pyspiel.load_game("oware").new_initial_state()

    while not theirs.is_terminal() and len(ours.moves) < OPENSPIEL_MAX_MOVES:
        assert not ours.is_over
        assert ours.position.to_move.value == theirs.current_player()
        # OpenSpiel's action k is the mover's pit k + 1, counted from their own left.
        assert ours.position.legal_moves() == [a + 1 for a in theirs.legal_actions()]

        action = rng.choice(theirs.legal_actions())
        ours.play(action + 1)
        theirs.apply_action(action)

        assert (ours.position.board, ours.position.stores) == openspiel_view(theirs), f"after moves {ours.moves}"

    if theirs.is_terminal():
        assert ours.is_over
        south_return = theirs.returns()[0]
        expected_winner = {1: Side.SOUTH, -1: Side.NORTH, 0: None}[south_return]
        assert ours.result.winner == expected_winner
