"""The Deepening agent: AlphaBeta's moves in a better order, deeper and deeper until the time is up."""

import time

import pytest

from awale.agents import AlphaBetaAgent, DeepeningAgent, make_agent
from awale.agents.heuristics import HEURISTICS
from awale.agents.minimax_agent import WIN
from awale.engine import Position, Side
from awale.tournament import run_tournament
from test_alphabeta_agent import GREEDY_TRAP, play_whole_game, some_positions

# The positions from test_minimax_agent.py where a game ends inside the look-ahead.
ENDINGS = [
    Position.setup(south=(1, 0, 0, 0, 0, 1), north=(1, 4, 4, 4, 4, 4), stores=(23, 2)),
    Position.setup(south=(1, 0, 0, 1, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(21, 23)),
    Position.setup(south=(0, 0, 0, 0, 0, 1), north=(3, 0, 0, 0, 0, 0), stores=(24, 20)),
    Position.setup(south=(1, 7, 7, 0, 6, 6), north=(5, 5, 5, 5, 0, 1), to_move=Side.NORTH),
]


def assert_thinks_like_alphabeta(position, depth, heuristic="store"):
    alphabeta = AlphaBetaAgent(seed=0, depth=depth, heuristic=HEURISTICS[heuristic]).think(position)
    deepening = DeepeningAgent(seed=0, depth=depth, heuristic=HEURISTICS[heuristic]).think(position)

    assert deepening.move == alphabeta.move
    assert deepening.depth == depth
    assert deepening.line[:1] == alphabeta.line[:1]
    assert deepening.scores.keys() == alphabeta.scores.keys()
    for pit, score in deepening.scores.items():
        if pit in deepening.upper_bounds:
            # "This or less": never below the true score, and below the best move's score.
            assert alphabeta.scores[pit] <= score < deepening.scores[deepening.move]
        else:
            assert score == alphabeta.scores[pit]


@pytest.mark.parametrize("depth", [1, 2, 3, 4, 5])
def test_at_a_fixed_depth_it_chooses_the_moves_alphabeta_chooses(depth):
    # The same move from the same seed, the same exact scores, and bounds where it skipped the exact score.
    for position in some_positions():
        assert_thinks_like_alphabeta(position, depth)


def test_it_chooses_like_alphabeta_with_the_mix_heuristic_too():
    # `mix` scores have decimals, so this checks that a tie is still found as a tie.
    for position in some_positions(20):
        assert_thinks_like_alphabeta(position, 4, "mix")


def test_it_chooses_like_alphabeta_where_the_game_ends():
    # It may stop before depth 4 here (see the tests below). A win scores WIN plus the depth still left,
    # so a win in 1 move scores 100 when it stops at depth 1, and 103 at depth 4. Both are the same win.
    for position in ENDINGS:
        alphabeta = AlphaBetaAgent(seed=0, depth=4).think(position)
        deepening = DeepeningAgent(seed=0, depth=4).think(position)

        assert deepening.move == alphabeta.move
        best = deepening.scores[deepening.move]
        if best >= WIN:
            assert best - deepening.depth == alphabeta.scores[alphabeta.move] - 4
        else:
            assert best == alphabeta.scores[alphabeta.move]


def test_plays_the_same_games_as_alphabeta():
    for seed in range(3):
        alphabeta = play_whole_game(AlphaBetaAgent(seed, depth=3), AlphaBetaAgent(seed + 100, depth=2))
        deepening = play_whole_game(DeepeningAgent(seed, depth=3), DeepeningAgent(seed + 100, depth=2))

        assert deepening == alphabeta


def test_the_same_tournament_as_alphabeta_gives_the_same_results():
    alphabeta = run_tournament("AlphaBeta:3:mix", "Greedy", openings=10, seed=0, workers=1)
    deepening = run_tournament("Deepening:3:mix", "Greedy", openings=10, seed=0, workers=1)

    assert deepening.points() == alphabeta.points()
    assert deepening.seed_differences() == alphabeta.seed_differences()


def test_looks_at_fewer_positions_than_alphabeta_deep_down():
    # All the shallower searches are counted too, and it still does less work.
    mix = HEURISTICS["mix"]
    positions = some_positions(10)
    alphabeta = sum(AlphaBetaAgent(seed=0, depth=7, heuristic=mix).think(p).positions for p in positions)
    deepening = sum(DeepeningAgent(seed=0, depth=7, heuristic=mix).think(p).positions for p in positions)

    assert deepening < alphabeta * 0.85


def test_worse_moves_get_only_an_upper_bound():
    # The example in docs/agents/deepening.md. Pit 6 is tried first and scores 0. Every other move is only
    # proved to be worse: pit 4 is "-7 or less", and in fact it is -9.
    thoughts = DeepeningAgent(seed=0, depth=6).think(GREEDY_TRAP)

    assert thoughts.move == 6
    assert thoughts.scores == {1: -7, 2: -3, 3: -4, 4: -7, 6: 0}
    assert thoughts.upper_bounds == {1, 2, 3, 4}
    assert AlphaBetaAgent(seed=0, depth=6).think(GREEDY_TRAP).scores[4] == -9


def test_tries_the_last_best_move_first_then_the_biggest_captures():
    agent = DeepeningAgent(depth=3)

    # Pits 2 and 6 capture 2 seeds each, the others nothing. Equal captures stay in pit order.
    assert [pit for pit, _ in agent.ordered_moves(GREEDY_TRAP)] == [2, 6, 1, 3, 4]

    agent.best_moves[GREEDY_TRAP] = 3  # as if pit 3 was the best move here in the last search
    assert [pit for pit, _ in agent.ordered_moves(GREEDY_TRAP)] == [3, 2, 6, 1, 4]


def test_a_value_outside_the_window_is_only_a_bound():
    # The same promise as AlphaBeta's, with the moves in a different order.
    alphabeta, deepening = AlphaBetaAgent(depth=3), DeepeningAgent(depth=3)
    for position in some_positions(15):
        me = position.to_move
        exact, _ = alphabeta.alphabeta(position, 3, me, -float("inf"), float("inf"))
        for alpha, beta in [(exact - 3, exact + 3), (exact + 1, exact + 5), (exact - 5, exact - 1)]:
            value, _ = deepening.alphabeta(position, 3, me, alpha, beta)
            if alpha < exact < beta:
                assert value == exact
            elif exact <= alpha:
                assert exact <= value <= alpha
            else:
                assert beta <= value <= exact


def test_stops_when_the_time_is_up():
    position = some_positions(3)[2]
    started = time.perf_counter()
    thoughts = DeepeningAgent(seed=0, time_limit=0.05).think(position)
    seconds = time.perf_counter() - started

    assert seconds < 0.05 + 0.02  # a little extra for Python to notice and leave the search
    assert thoughts.depth >= 3
    assert thoughts.move in position.legal_moves()


def test_more_time_looks_deeper():
    position = some_positions(3)[2]
    quick = DeepeningAgent(seed=0, time_limit=0.01).think(position)
    slow = DeepeningAgent(seed=0, time_limit=0.2).think(position)

    assert slow.depth > quick.depth


def test_even_with_almost_no_time_it_looks_one_move_ahead():
    thoughts = DeepeningAgent(seed=0, time_limit=0.000001).think(GREEDY_TRAP)

    assert thoughts.depth == 1
    assert thoughts.scores == {1: 0, 2: 2, 3: 0, 4: 0, 6: 2}  # like Greedy


def test_stops_looking_deeper_when_every_line_ends_the_game():
    # South's only move sows its last seed into North's row, and the game ends in a draw at once.
    # A longer search could not change anything, so it stops after 1 move instead of thinking for 10 seconds.
    thoughts = DeepeningAgent(seed=0, time_limit=10).think(ENDINGS[2])

    assert (thoughts.depth, thoughts.scores) == (1, {6: 0})


def test_stops_looking_deeper_once_it_surely_wins():
    # South has 23, and its pit 6 captures 2 from North's pit 1: a win in one move.
    started = time.perf_counter()
    thoughts = DeepeningAgent(seed=0, time_limit=10).think(ENDINGS[0])

    assert time.perf_counter() - started < 1
    assert thoughts.move == 6
    assert thoughts.scores[6] >= WIN


def test_thinks_for_a_tenth_of_a_second_unless_told_otherwise():
    agent = make_agent("Deepening")

    assert (agent.depth, agent.time_limit) == (None, 0.1)
    assert agent.heuristic is HEURISTICS["store"]


def test_make_agent_sets_a_depth_a_time_limit_or_both():
    assert (make_agent("Deepening:8").depth, make_agent("Deepening:8").time_limit) == (8, None)
    assert (make_agent("Deepening:0.5s").depth, make_agent("Deepening:0.5s").time_limit) == (None, 0.5)

    both = make_agent("Deepening:mix:12:2s")  # any order
    assert (both.depth, both.time_limit, both.heuristic) == (12, 2.0, HEURISTICS["mix"])
    assert both.name == "Deepening:mix:12:2s"


@pytest.mark.parametrize(
    "name", ["Deepening:0s", "Deepening:-1s", "Deepening:1s:2s", "Deepening:fasts", "AlphaBeta:1s"]
)
def test_make_agent_refuses_a_time_limit_it_cannot_use(name):
    with pytest.raises(ValueError):
        make_agent(name)


def test_needs_a_depth_of_at_least_1_and_a_time_above_0():
    with pytest.raises(ValueError, match="Deepening needs a depth"):
        DeepeningAgent(depth=0)
    with pytest.raises(ValueError, match="Deepening needs a time limit"):
        DeepeningAgent(time_limit=0)
