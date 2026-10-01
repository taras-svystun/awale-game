"""How a whole game ends, and undo."""

import pytest

from awale.engine import Game, Position, Side


def test_new_game_is_not_over():
    game = Game(first=Side.NORTH)

    assert game.position == Position.start(first=Side.NORTH)
    assert not game.is_over
    assert game.result is None


def test_game_ends_when_a_store_reaches_25_and_seeds_left_go_to_the_row_owner():
    game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4), stores=(23, 0)))

    game.play(6)  # South captures 2 and reaches 25. North still has 21 seeds in its row.

    assert game.is_over
    assert game.result.winner == Side.SOUTH
    assert game.result.score == (25, 21)


def test_when_the_opponent_cannot_be_fed_each_player_takes_their_own_row():
    game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 0), north=(0, 0, 0, 0, 0, 1), to_move=Side.NORTH, stores=(24, 23)))

    game.play(6)  # North feeds South with its last seed. Now South's 1 seed cannot reach North.

    assert game.is_over
    assert game.result.winner == Side.SOUTH
    assert game.result.score == (25, 23)
    assert game.position.pits(Side.SOUTH) == (0, 0, 0, 0, 0, 0)


def test_a_repeated_position_ends_the_game_and_each_player_takes_their_own_row():
    game = Game(start=Position.setup(south=(1, 0, 0, 0, 0, 0), north=(1, 0, 0, 0, 0, 0), stores=(23, 23)))

    # Each seed walks one pit per move. After 6 moves each, the board is back where it started.
    for south_pit, north_pit in zip(range(1, 7), range(1, 7)):
        assert not game.is_over
        game.play(south_pit)
        game.play(north_pit)

    assert game.is_over
    assert game.result.winner is None
    assert game.result.score == (24, 24)


def test_undo_takes_back_the_last_move():
    game = Game()
    game.play(3)
    after_first_move = game.position
    game.play(1)

    game.undo()

    assert game.position == after_first_move
    assert game.moves == [3]


def test_undo_after_the_game_ended_early_makes_it_playable_again():
    before = Position.setup(south=(0, 0, 0, 0, 0, 0), north=(0, 0, 0, 0, 0, 1), to_move=Side.NORTH, stores=(24, 23))
    game = Game(start=before)
    game.play(6)

    game.undo()

    assert not game.is_over
    assert game.position == before


def test_undo_at_the_start_raises_an_error():
    with pytest.raises(ValueError):
        Game().undo()


def test_a_copy_of_a_game_does_not_change_with_it():
    game = Game()
    game.play(3)
    copy = game.copy()
    game.play(2)
    copy.undo()

    assert game.moves == [3, 2]
    assert copy.moves == []
    assert copy.position == Position.start()
