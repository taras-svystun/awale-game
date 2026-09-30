"""The AlphaBeta agent: the same moves as Minimax, from fewer positions."""

import random
from dataclasses import replace

import pytest

from awale.agents import AlphaBetaAgent, MinimaxAgent, RandomAgent, make_agent
from awale.agents.alphabeta_agent import INFINITY
from awale.engine import Game, Position, Side
from awale.tournament import run_tournament

# The position from docs/agents/greedy.md and minimax.md.
GREEDY_TRAP = Position.setup(south=(5, 5, 5, 5, 0, 1), north=(1, 7, 7, 0, 6, 6))


def some_positions(count: int = 30) -> list[Position]:
    """Positions from random games, at many stages, where the game is not over."""
    rng = random.Random(3)
    positions = [Position.start(), GREEDY_TRAP]
    while len(positions) < count:
        game = Game()
        random_agent = RandomAgent(rng.randrange(10**6))
        for _ in range(rng.randrange(4, 50)):
            if game.is_over:
                break
            game.play(random_agent.choose_move(game.position))
        if not game.is_over:
            positions.append(game.position)
    return positions


def play_whole_game(south, north) -> list[int]:
    game = Game()
    agents = [south, north]
    while not game.is_over:
        game.play(agents[game.position.to_move.value].choose_move(game.position))
    return game.moves


@pytest.mark.parametrize("depth", [1, 2, 3, 4, 5])
def test_thinks_exactly_like_minimax(depth):
    # The same move, the same score for every move, the same expected line. Only the work done differs.
    for position in some_positions():
        minimax = MinimaxAgent(seed=0, depth=depth).think(position)
        alphabeta = AlphaBetaAgent(seed=0, depth=depth).think(position)

        assert replace(alphabeta, positions=0) == replace(minimax, positions=0)


def test_thinks_like_minimax_about_wins_losses_and_the_end_of_the_game():
    # The positions from test_minimax_agent.py where a game ends inside the look-ahead.
    positions = [
        Position.setup(south=(1, 0, 0, 0, 0, 1), north=(1, 4, 4, 4, 4, 4), stores=(23, 2)),
        Position.setup(south=(1, 0, 0, 1, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(21, 23)),
        Position.setup(south=(0, 0, 0, 0, 0, 1), north=(3, 0, 0, 0, 0, 0), stores=(24, 20)),
        Position.setup(south=(1, 7, 7, 0, 6, 6), north=(5, 5, 5, 5, 0, 1), to_move=Side.NORTH),
    ]
    for position in positions:
        minimax = MinimaxAgent(seed=0, depth=4).think(position)
        alphabeta = AlphaBetaAgent(seed=0, depth=4).think(position)

        assert replace(alphabeta, positions=0) == replace(minimax, positions=0)


def test_looks_at_fewer_positions_than_minimax():
    # At depth 2 there is nothing to skip: every move gets its exact score, and those are all answers to it.
    # From depth 3 on, whole branches are skipped, and more of them the deeper it looks.
    start = Position.start()
    positions = {depth: AlphaBetaAgent(seed=0, depth=depth).think(start).positions for depth in (2, 4, 6)}

    assert positions[2] == MinimaxAgent(seed=0, depth=2).think(start).positions == 6 + 6 * 6
    assert positions[4] < MinimaxAgent(seed=0, depth=4).think(start).positions / 2
    assert positions[6] < MinimaxAgent(seed=0, depth=6).think(start).positions / 5


def test_skips_the_answers_that_cannot_change_the_choice():
    # The example in docs/agents/alphabeta.md. After South's pit 3, North's pit 1 holds South to 0.
    # After North's pit 2 instead, South's pit 1 captures 3 at once. So North will not play pit 2,
    # and South's other 5 answers to it are skipped. The same happens after North's pits 3 and 5.
    after_c = GREEDY_TRAP.play(3)
    agent = AlphaBetaAgent(depth=3)

    value, line = agent.alphabeta(after_c, 2, Side.SOUTH, -INFINITY, INFINITY)

    assert (value, line) == (-2, (6, 1))
    # North's 5 answers, South's 5 answers to pit 1, 1 to each of pits 2, 3 and 5, and 4 to pit 6.
    assert agent.positions == 5 + 5 + 1 + 1 + 1 + 4


def test_a_value_outside_the_window_is_only_a_bound():
    # This is the promise in the alphabeta docstring, checked against Minimax's exact value.
    minimax, alphabeta = MinimaxAgent(depth=3), AlphaBetaAgent(depth=3)
    for position in some_positions(15):
        me = position.to_move
        exact, _ = minimax.minimax(position, 3, me)
        for alpha, beta in [(exact - 3, exact + 3), (exact + 1, exact + 5), (exact - 5, exact - 1)]:
            value, _ = alphabeta.alphabeta(position, 3, me, alpha, beta)
            if alpha < exact < beta:
                assert value == exact
            elif exact <= alpha:
                assert exact <= value <= alpha  # "alpha or less", and never less than the truth
            else:
                assert beta <= value <= exact  # "beta or more", and never more than the truth


def test_plays_the_same_games_as_minimax():
    for seed in range(3):
        minimax = play_whole_game(MinimaxAgent(seed, depth=3), MinimaxAgent(seed + 100, depth=2))
        alphabeta = play_whole_game(AlphaBetaAgent(seed, depth=3), AlphaBetaAgent(seed + 100, depth=2))

        assert alphabeta == minimax


def test_the_same_tournament_as_minimax_gives_the_same_results():
    # Same seed, same games, same moves: only the time per move differs.
    minimax = run_tournament("Minimax:3", "Greedy", openings=10, seed=0, workers=1)
    alphabeta = run_tournament("AlphaBeta:3", "Greedy", openings=10, seed=0, workers=1)

    assert alphabeta.points() == minimax.points()
    assert alphabeta.seed_differences() == minimax.seed_differences()


def test_looks_6_moves_ahead_unless_told_otherwise():
    assert AlphaBetaAgent().depth == 6
    assert make_agent("AlphaBeta").depth == 6
    assert make_agent("AlphaBeta:8").depth == 8


def test_needs_a_depth_of_at_least_1():
    with pytest.raises(ValueError, match="AlphaBeta needs a depth"):
        AlphaBetaAgent(depth=0)
