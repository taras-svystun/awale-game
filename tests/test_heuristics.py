"""Heuristics and the board features they are made of."""

import pytest

from awale.agents import AlphaBetaAgent
from awale.agents.heuristics import HEURISTICS, big_pits, mobility, row_seeds, store_diff, weak_pits, weighted
from awale.agents.minimax_agent import WIN
from awale.engine import Position, Side
from awale.tournament import mean_and_margin, run_tournament

# South: 1 seed in pit 1, 2 in pit 2, an empty pit 3, and a big pit 6.
# North: one weak pit (pit 6), two empty pits.
POSITION = Position.setup(south=(1, 2, 0, 3, 4, 13), north=(5, 0, 6, 0, 4, 2), stores=(7, 1))


def test_store_diff_counts_the_captured_seeds():
    assert store_diff(POSITION, Side.SOUTH) == 7 - 1


def test_row_seeds_counts_the_seeds_in_each_row():
    assert row_seeds(POSITION, Side.SOUTH) == 23 - 17


def test_weak_pits_are_the_opponents_pits_with_1_or_2_seeds_minus_mine():
    # North's pit 6 holds 2. South's pits 1 and 2 hold 1 and 2. Empty pits and pits with 3 are not weak.
    assert weak_pits(POSITION, Side.SOUTH) == 1 - 2


def test_mobility_counts_the_pits_that_are_not_empty():
    assert mobility(POSITION, Side.SOUTH) == 5 - 4


def test_big_pits_count_pits_with_12_seeds_or_more():
    assert big_pits(POSITION, Side.SOUTH) == 1
    assert big_pits(Position.setup(south=(11, 0, 0, 0, 0, 0), north=(12, 0, 0, 0, 0, 0)), Side.SOUTH) == -1


@pytest.mark.parametrize("heuristic", [store_diff, row_seeds, weak_pits, mobility, big_pits])
def test_what_is_good_for_one_player_is_as_bad_for_the_other(heuristic):
    assert heuristic(POSITION, Side.NORTH) == -heuristic(POSITION, Side.SOUTH)


def test_weighted_adds_each_feature_times_its_weight_to_store_diff():
    heuristic = weighted({row_seeds: 0.25, weak_pits: 0.5})

    assert heuristic(POSITION, Side.SOUTH) == 6 + 0.25 * 6 + 0.5 * -1
    assert heuristic(POSITION, Side.NORTH) == -heuristic(POSITION, Side.SOUTH)


# The most each feature can be: all 48 seeds in one row, 6 pits, 4 pits with 12 seeds.
MOST = {row_seeds: 48, weak_pits: 6, mobility: 6, big_pits: 4}


@pytest.mark.parametrize("name", HEURISTICS)
def test_no_position_looks_as_good_as_a_won_game(name):
    # A search scores a won game WIN or more. A guess about a position that is not over must stay below that,
    # or the search could prefer a nice-looking position to a real win.
    weights = getattr(HEURISTICS[name], "weights", {})

    assert 48 + sum(abs(weight) * MOST[feature] for feature, weight in weights.items()) < WIN


def test_mix_beats_store_diff_clearly():
    tournament = run_tournament("AlphaBeta:2:mix", "AlphaBeta:2", openings=30, seed=0, workers=1)

    points, margin = mean_and_margin(tournament.points())
    assert points - margin > 0.5


def test_mix_sees_what_store_diff_cannot_on_a_quiet_position():
    # The example in docs/agents/heuristics.md. No capture is possible within 2 moves, so store_diff
    # scores every move 0. Mix prefers pit 3: it keeps the seeds at home and leaves North 2 empty pits.
    position = Position.setup(south=(0, 11, 3, 7, 8, 1), north=(0, 8, 0, 4, 4, 2))

    store = AlphaBetaAgent(seed=0, depth=2).think(position)
    mix = AlphaBetaAgent(seed=0, depth=2, heuristic=HEURISTICS["mix"]).think(position)

    assert store.scores == {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    assert mix.scores == {2: 0, 3: 2.6, 4: -0.3, 5: 0, 6: 1}
    assert mix.move == 3
    assert mix.line == (3, 4)
