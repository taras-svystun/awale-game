"""Rules of a single move, checked on small positions worked out by hand.

Pits are always listed from the owner's own left, pit 1 first.
"""

import pytest

from awale.engine import Position, Side


def test_start_position_has_four_seeds_in_every_pit():
    pos = Position.start(first=Side.SOUTH)

    assert pos.pits(Side.SOUTH) == (4, 4, 4, 4, 4, 4)
    assert pos.pits(Side.NORTH) == (4, 4, 4, 4, 4, 4)
    assert pos.store(Side.SOUTH) == 0
    assert pos.store(Side.NORTH) == 0
    assert pos.to_move == Side.SOUTH
    assert pos.legal_moves() == [1, 2, 3, 4, 5, 6]


def test_sowing_drops_one_seed_in_each_next_pit_and_passes_the_turn():
    before = Position.start(first=Side.SOUTH)

    after = before.play(3)

    assert after.pits(Side.SOUTH) == (4, 4, 0, 5, 5, 5)
    assert after.pits(Side.NORTH) == (5, 4, 4, 4, 4, 4)
    assert after.to_move == Side.NORTH
    assert before.pits(Side.SOUTH) == (4, 4, 4, 4, 4, 4), "play() must not change the old position"


def test_north_sows_from_its_own_pit_1_towards_pit_6_then_into_south():
    pos = Position.start(first=Side.NORTH).play(6)

    assert pos.pits(Side.NORTH) == (4, 4, 4, 4, 4, 0)
    assert pos.pits(Side.SOUTH) == (5, 5, 5, 5, 4, 4)
    assert pos.to_move == Side.SOUTH


def test_a_pit_with_12_or_more_seeds_is_skipped_when_the_seeds_go_around():
    pos = Position.setup(south=(12, 0, 0, 0, 0, 0), north=(4, 4, 4, 4, 4, 4))

    after = pos.play(1)

    # 11 seeds go around to the other 11 pits, the 12th skips pit 1 and lands in pit 2.
    assert after.pits(Side.SOUTH) == (0, 2, 1, 1, 1, 1)
    assert after.pits(Side.NORTH) == (5, 5, 5, 5, 5, 5)


def test_last_seed_making_2_or_3_in_opponents_pit_captures_them():
    pos = Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4))

    after = pos.play(6)

    assert after.pits(Side.NORTH) == (5, 0, 4, 4, 4, 4)
    assert after.store(Side.SOUTH) == 2


def test_capture_goes_back_through_pits_with_2_or_3_and_stops_at_the_first_other_pit():
    pos = Position.setup(south=(0, 0, 0, 0, 0, 5), north=(1, 2, 5, 1, 2, 4))

    after = pos.play(6)

    # Sowing makes North (2, 3, 6, 2, 3, 4). Pits 5 and 4 are captured, pit 3 (6 seeds)
    # stops the chain, so pits 1 and 2 stay even though they hold 2 and 3.
    assert after.pits(Side.NORTH) == (2, 3, 6, 0, 0, 4)
    assert after.store(Side.SOUTH) == 5


def test_capture_chain_never_takes_seeds_from_the_movers_own_row():
    pos = Position.setup(south=(1, 1, 4, 4, 4, 4), north=(0, 0, 0, 0, 3, 1), to_move=Side.NORTH)

    after = pos.play(5)

    # North's own pit 6 now holds 2, but it is North's, so the chain stops there.
    assert after.pits(Side.SOUTH) == (0, 0, 4, 4, 4, 4)
    assert after.pits(Side.NORTH) == (0, 0, 0, 0, 0, 2)
    assert after.store(Side.NORTH) == 4


def test_grand_slam_captures_nothing():
    pos = Position.setup(south=(0, 0, 0, 0, 0, 2), north=(1, 1, 0, 0, 0, 0))

    after = pos.play(6)

    # Capturing both pits would leave North with no seeds, so nothing is captured.
    assert after.pits(Side.NORTH) == (2, 2, 0, 0, 0, 0)
    assert after.store(Side.SOUTH) == 0


def test_when_opponents_row_is_empty_only_moves_that_feed_them_are_legal():
    pos = Position.setup(south=(3, 1, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 0))

    # Pit 1 (3 seeds) and pit 2 (1 seed) stay in South's row, only pit 6 reaches North.
    assert pos.legal_moves() == [6]


def test_when_no_move_can_feed_the_opponent_there_are_no_legal_moves():
    pos = Position.setup(south=(1, 0, 0, 0, 0, 0), north=(0, 0, 0, 0, 0, 0))

    assert pos.legal_moves() == []


def test_playing_an_illegal_move_raises_an_error():
    pos = Position.setup(south=(3, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 0))

    with pytest.raises(ValueError):
        pos.play(2)  # empty pit
    with pytest.raises(ValueError):
        pos.play(1)  # does not feed North
