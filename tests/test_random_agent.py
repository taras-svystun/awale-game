"""The Random agent."""

from collections import Counter

from awale.agents import RandomAgent
from awale.engine import Game, Position


def play_whole_game(south, north) -> list[int]:
    game = Game()
    agents = [south, north]
    while not game.is_over:
        agent = agents[game.position.to_move.value]
        move = agent.choose_move(game.position)
        assert move in game.position.legal_moves()
        game.play(move)
    return game.moves


def test_plays_only_legal_moves_until_the_game_ends():
    for seed in range(20):
        play_whole_game(RandomAgent(seed), RandomAgent(seed + 100))


def test_plays_the_only_legal_move():
    # North's row is empty, and only pit 6 can reach it (feeding).
    position = Position.setup(south=(2, 0, 0, 0, 0, 1), north=(0, 0, 0, 0, 0, 0))

    assert position.legal_moves() == [6]
    for seed in range(10):
        assert RandomAgent(seed).choose_move(position) == 6


def test_chooses_every_legal_move_about_equally_often():
    agent = RandomAgent(seed=0)

    counts = Counter(agent.choose_move(Position.start()) for _ in range(600))

    assert set(counts) == {1, 2, 3, 4, 5, 6}
    # About 100 each. Anything outside 50-150 is almost impossible for a fair choice.
    assert all(50 <= count <= 150 for count in counts.values()), counts


def test_the_same_seed_plays_the_same_game():
    first = play_whole_game(RandomAgent(seed=1), RandomAgent(seed=2))
    again = play_whole_game(RandomAgent(seed=1), RandomAgent(seed=2))
    other = play_whole_game(RandomAgent(seed=3), RandomAgent(seed=4))

    assert first == again
    assert first != other
