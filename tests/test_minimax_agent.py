"""The Minimax agent."""

from collections import Counter

import pytest

from awale.agents import GreedyAgent, MinimaxAgent, RandomAgent
from awale.agents.minimax_agent import WIN
from awale.engine import Game, Position, Side
from awale.tournament import mean_and_margin, run_tournament

# The position from docs/agents/greedy.md: pits 2 and 6 both capture 2, but after pit 2 North captures 5.
GREEDY_TRAP = Position.setup(south=(5, 5, 5, 5, 0, 1), north=(1, 7, 7, 0, 6, 6))


def play_whole_game(south, north) -> list[int]:
    game = Game()
    agents = [south, north]
    while not game.is_over:
        agent = agents[game.position.to_move.value]
        move = agent.choose_move(game.position)
        assert move in game.position.legal_moves()
        game.play(move)
    return game.moves


def test_at_depth_1_it_scores_moves_like_greedy():
    # With both stores at 0, "my store minus theirs" after one move is just what that move captures.
    minimax = MinimaxAgent(seed=0, depth=1).think(GREEDY_TRAP)
    greedy = GreedyAgent(seed=0).think(GREEDY_TRAP)

    assert minimax.scores == greedy.scores == {1: 0, 2: 2, 3: 0, 4: 0, 6: 2}


def test_at_depth_2_it_sees_the_capture_it_gives_away():
    # Pit 2 captures 2, then North captures 5: 2 - 5 = -3. Pit 6 captures 2 and North has nothing: +2.
    # Pits 1, 3 and 4 capture nothing and let North capture 5.
    thoughts = MinimaxAgent(seed=0, depth=2).think(GREEDY_TRAP)

    assert thoughts.scores == {1: -5, 2: -3, 3: -5, 4: -5, 6: 2}
    assert thoughts.move == 6
    assert thoughts.line == (6, 2)


def test_scores_for_north_when_playing_north():
    # The same board as GREEDY_TRAP, seen from North's side.
    position = Position.setup(south=(1, 7, 7, 0, 6, 6), north=(5, 5, 5, 5, 0, 1), to_move=Side.NORTH)

    thoughts = MinimaxAgent(seed=0, depth=2).think(position)

    assert thoughts.scores == {1: -5, 2: -3, 3: -5, 4: -5, 6: 2}
    assert thoughts.move == 6


def test_takes_a_win_and_scores_it_above_any_seed_count():
    # South has 23 seeds. Pit 6 makes North's pit 1 hold 2: South captures them, reaches 25 and wins.
    position = Position.setup(south=(1, 0, 0, 0, 0, 1), north=(1, 4, 4, 4, 4, 4), stores=(23, 2))

    thoughts = MinimaxAgent(seed=0, depth=4).think(position)

    assert thoughts.move == 6
    # A win found after 1 move, with 3 more moves of depth left: a quicker win scores higher.
    assert thoughts.scores[6] == WIN + 3
    assert thoughts.line == (6,)  # the game ends there, so the line does too


def test_avoids_a_move_that_lets_the_opponent_win():
    # North has 23 seeds, and its pit 6 drops one seed into South's pit 1.
    # If South's pit 1 still holds 1 seed then, North captures 2 and wins. Only pit 1 empties it.
    position = Position.setup(south=(1, 0, 0, 1, 0, 1), north=(0, 0, 0, 0, 0, 1), stores=(21, 23))

    greedy = GreedyAgent(seed=0).think(position)
    minimax = MinimaxAgent(seed=0, depth=2).think(position)

    assert greedy.scores == {1: 0, 4: 0, 6: 0}  # Greedy cannot tell them apart
    assert minimax.scores == {1: -2, 4: -WIN, 6: -WIN}
    assert minimax.move == 1


def test_at_the_end_of_the_game_the_seeds_left_go_to_each_row():
    # After pit 6, South's row is empty and North's 4 seeds cannot reach it: the game ends.
    # South keeps 24, North gets 20 + 4 = 24: a draw, not "4 seeds ahead" as the stores alone would say.
    position = Position.setup(south=(0, 0, 0, 0, 0, 1), north=(3, 0, 0, 0, 0, 0), stores=(24, 20))

    thoughts = MinimaxAgent(seed=0).think(position)

    assert thoughts.scores == {6: 0}


def test_its_line_is_a_real_line_of_play():
    thoughts = MinimaxAgent(seed=0, depth=4).think(GREEDY_TRAP)

    assert len(thoughts.line) == 4
    assert thoughts.line[0] == thoughts.move
    position = GREEDY_TRAP
    for pit in thoughts.line:
        position = position.play(pit)  # raises if a move in the line is not legal


def test_counts_the_positions_it_looked_at():
    # From the start: 6 moves, then 6 answers to each. No move captures, so no game ends early.
    thoughts = MinimaxAgent(seed=0, depth=2).think(Position.start())

    assert thoughts.positions == 6 + 6 * 6
    assert thoughts.depth == 2


def test_breaks_ties_at_random():
    # From the start nothing can be captured in 2 moves, so every pit scores 0.
    counts = Counter(MinimaxAgent(seed, depth=2).choose_move(Position.start()) for seed in range(600))

    assert set(counts) == {1, 2, 3, 4, 5, 6}
    assert all(50 <= count <= 150 for count in counts.values()), counts


def test_needs_a_depth_of_at_least_1():
    with pytest.raises(ValueError, match="depth"):
        MinimaxAgent(depth=0)


def test_plays_only_legal_moves_until_the_game_ends():
    for seed in range(5):
        play_whole_game(MinimaxAgent(seed, depth=2), RandomAgent(seed + 100))
        play_whole_game(MinimaxAgent(seed, depth=3), GreedyAgent(seed + 100))


def test_the_same_seed_plays_the_same_game():
    first = play_whole_game(MinimaxAgent(seed=1, depth=2), MinimaxAgent(seed=2, depth=2))
    again = play_whole_game(MinimaxAgent(seed=1, depth=2), MinimaxAgent(seed=2, depth=2))
    other = play_whole_game(MinimaxAgent(seed=3, depth=2), MinimaxAgent(seed=4, depth=2))

    assert first == again
    assert first != other


def test_beats_greedy_clearly():
    # Depth 2 is enough, and quick: it sees the captures Greedy gives away.
    tournament = run_tournament("Minimax:2", "Greedy", openings=50, seed=0, workers=1)

    points, margin = mean_and_margin(tournament.points())
    assert points - margin > 0.5
