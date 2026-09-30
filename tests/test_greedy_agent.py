"""The Greedy agent."""

from collections import Counter

from awale.agents import GreedyAgent, RandomAgent
from awale.engine import Game, Position, Side
from awale.tournament import mean_and_margin, run_tournament


def play_whole_game(south, north) -> list[int]:
    game = Game()
    agents = [south, north]
    while not game.is_over:
        agent = agents[game.position.to_move.value]
        move = agent.choose_move(game.position)
        assert move in game.position.legal_moves()
        game.play(move)
    return game.moves


def test_takes_the_capture():
    # Pit 6 makes North's pits 1 and 2 hold 2 and 3 seeds: 5 seeds captured. Pit 1 captures nothing.
    position = Position.setup(south=(1, 0, 0, 0, 0, 2), north=(1, 2, 4, 4, 4, 4))

    thoughts = GreedyAgent(seed=0).think(position)

    assert thoughts.move == 6
    assert thoughts.scores == {1: 0, 6: 5}


def test_takes_the_bigger_of_two_captures():
    # Pit 5 ends in North's pit 1 (1 -> 2): 2 seeds.
    # Pit 6 ends in North's pit 2 (2 -> 3), then goes back to pit 1 (1 -> 2): 5 seeds.
    position = Position.setup(south=(0, 0, 0, 0, 2, 2), north=(1, 2, 4, 4, 4, 4))

    thoughts = GreedyAgent(seed=0).think(position)

    assert thoughts.scores == {5: 2, 6: 5}
    assert thoughts.move == 6


def test_scores_its_own_capture_when_playing_north():
    # The same board as in test_takes_the_capture, seen from North's side.
    position = Position.setup(south=(1, 2, 4, 4, 4, 4), north=(1, 0, 0, 0, 0, 2), to_move=Side.NORTH)

    thoughts = GreedyAgent(seed=0).think(position)

    assert thoughts.move == 6
    assert thoughts.scores == {1: 0, 6: 5}


def test_a_grand_slam_scores_nothing():
    # Pit 6 makes North's pits 1 and 2 hold 2 and 2. Taking them would take all of North's row:
    # that is a grand slam, so it captures nothing and is no better than pit 1.
    position = Position.setup(south=(1, 0, 0, 0, 0, 2), north=(1, 1, 0, 0, 0, 0))

    thoughts = GreedyAgent(seed=0).think(position)

    assert thoughts.scores == {1: 0, 6: 0}


def test_breaks_ties_at_random():
    # From the start no move captures anything, so every pit is equally good.
    counts = Counter(GreedyAgent(seed).choose_move(Position.start()) for seed in range(600))

    assert set(counts) == {1, 2, 3, 4, 5, 6}
    assert all(50 <= count <= 150 for count in counts.values()), counts


def test_shows_one_move_ahead():
    position = Position.setup(south=(1, 0, 0, 0, 0, 2), north=(1, 2, 4, 4, 4, 4))

    thoughts = GreedyAgent(seed=0).think(position)

    assert thoughts.line == (6,)
    assert thoughts.depth == 1
    assert thoughts.positions == 2  # one position after each of its 2 legal moves


def test_plays_only_legal_moves_until_the_game_ends():
    for seed in range(10):
        play_whole_game(GreedyAgent(seed), RandomAgent(seed + 100))
        play_whole_game(GreedyAgent(seed), GreedyAgent(seed + 100))


def test_the_same_seed_plays_the_same_game():
    first = play_whole_game(GreedyAgent(seed=1), GreedyAgent(seed=2))
    again = play_whole_game(GreedyAgent(seed=1), GreedyAgent(seed=2))
    other = play_whole_game(GreedyAgent(seed=3), GreedyAgent(seed=4))

    assert first == again
    assert first != other


def test_beats_random_clearly():
    tournament = run_tournament("Greedy", "Random", openings=50, seed=0, workers=1)

    points, margin = mean_and_margin(tournament.points())
    assert points - margin > 0.5
