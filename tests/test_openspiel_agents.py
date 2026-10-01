"""OpenSpiel's agents: its MCTS and its alpha-beta, playing our games as outside opponents."""

import random
import time

import pytest

from awale.agents import AlphaBetaAgent, OpenSpielAlphaBetaAgent, OpenSpielMCTSAgent, RandomAgent, make_agent
from awale.agents.heuristics import HEURISTICS
from awale.agents.minimax_agent import WIN
from awale.agents.openspiel_agents import openspiel_state, position_of
from awale.engine import Game, Position, Side
from awale.tournament import run_tournament
from test_alphabeta_agent import GREEDY_TRAP


def some_games(count: int = 30, first: Side = Side.SOUTH) -> list[Game]:
    """Games of random moves, stopped at many stages before they end."""
    rng = random.Random(5)
    games = []
    while len(games) < count:
        game = Game(first=first)
        random_agent = RandomAgent(rng.randrange(10**6))
        for _ in range(rng.randrange(0, 60)):
            if game.is_over:
                break
            game.play(random_agent.choose_move(game.position))
        if not game.is_over:
            games.append(game)
    return games


def games_with_a_win_in_one_move(count: int = 5) -> list[tuple[Game, list[int]]]:
    """Games where the player to move can win right now, with the moves that win."""
    found = []
    for game in some_games(3000):
        position = game.position
        winning = [pit for pit in position.legal_moves() if position.play(pit).store(position.to_move) >= 25]
        if winning:
            found.append((game, winning))
            if len(found) == count:
                break
    return found


def mirrored(position: Position) -> Position:
    """The same position with South and North swapped."""
    return Position.setup(
        south=position.pits(Side.NORTH),
        north=position.pits(Side.SOUTH),
        to_move=position.to_move.opponent,
        stores=(position.stores[1], position.stores[0]),
    )


def test_openspiel_plays_the_whole_game_again_and_gets_our_position():
    for game in some_games():
        assert position_of(openspiel_state(game)) == game.position


def test_when_north_moved_first_openspiel_sees_the_board_turned_around():
    # OpenSpiel's player 0 always moves first, so here it is North.
    for game in some_games(10, first=Side.NORTH):
        assert position_of(openspiel_state(game)) == mirrored(game.position)


def test_openspiel_cannot_start_from_a_position_set_up_by_hand():
    with pytest.raises(ValueError, match="start position"):
        openspiel_state(Game(start=GREEDY_TRAP))
    with pytest.raises(ValueError, match="start position"):
        OpenSpielAlphaBetaAgent(depth=2).think(GREEDY_TRAP)


def test_with_only_a_position_it_can_think_about_the_start():
    for first in Side:
        assert OpenSpielAlphaBetaAgent(depth=2).think(Position.start(first)).move in range(1, 7)
        assert OpenSpielMCTSAgent(seed=0, playouts=50).think(Position.start(first)).move in range(1, 7)


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
@pytest.mark.parametrize("heuristic", ["store", "mix"])
def test_alphabeta_gives_every_move_the_score_our_alphabeta_gives(depth, heuristic):
    # Someone else's alpha-beta, with our heuristic, agrees with ours on every move.
    # Not where a game ends inside the look-ahead: OpenSpiel's win is worth exactly WIN, ours WIN plus the depth left.
    compared = 0
    for first in Side:
        for game in some_games(15, first):
            ours = AlphaBetaAgent(seed=0, depth=depth, heuristic=HEURISTICS[heuristic]).think(game.position)
            if max(abs(score) for score in ours.scores.values()) >= WIN:
                continue
            theirs = OpenSpielAlphaBetaAgent(depth=depth, heuristic=HEURISTICS[heuristic]).think_in_game(game)
            assert theirs.scores == pytest.approx(ours.scores)
            assert theirs.depth == depth
            compared += 1
    assert compared >= 20


def test_alphabeta_chooses_the_first_of_its_best_moves():
    # Unlike our agents, OpenSpiel's alpha-beta takes the leftmost of equally good moves, never a random one.
    thoughts = OpenSpielAlphaBetaAgent(depth=4).think(Position.start())

    assert thoughts.scores == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    assert thoughts.move == 1
    assert thoughts.line[0] == 1
    assert thoughts.positions > 0  # the positions where it called the heuristic


@pytest.mark.parametrize("agent", [OpenSpielAlphaBetaAgent(depth=2), OpenSpielMCTSAgent(seed=0, playouts=500)])
def test_takes_a_win_in_one_move(agent):
    for game, winning in games_with_a_win_in_one_move():
        assert agent.think_in_game(game).move in winning


def test_alphabeta_scores_a_win_as_win():
    game, winning = games_with_a_win_in_one_move(1)[0]
    thoughts = OpenSpielAlphaBetaAgent(depth=3).think_in_game(game)

    assert thoughts.scores[thoughts.move] == WIN


def test_mcts_thoughts():
    thoughts = OpenSpielMCTSAgent(seed=0, playouts=300).think(Position.start())

    assert thoughts.playouts == 300
    assert list(thoughts.scores) == [1, 2, 3, 4, 5, 6]
    assert all(0 <= score <= 1 for score in thoughts.scores.values())  # a share of wins, like our MCTS
    assert thoughts.line[0] == thoughts.move
    assert thoughts.depth >= len(thoughts.line)
    assert thoughts.positions == 299  # one position added to its tree by every playout but the first


def test_mcts_with_the_same_seed_gives_the_same_thoughts():
    for game in some_games(5):
        assert (
            OpenSpielMCTSAgent(seed=3, playouts=200).think_in_game(game)
            == OpenSpielMCTSAgent(seed=3, playouts=200).think_in_game(game)
        )


def test_mcts_with_one_playout_still_plays_a_legal_move():
    # OpenSpiel's first playout starts at the top and adds no move to its tree.
    for game in some_games(5):
        thoughts = OpenSpielMCTSAgent(seed=0, playouts=1).think_in_game(game)
        assert thoughts.move in game.position.legal_moves()
        assert thoughts.scores == {}


def test_mcts_stops_when_its_time_is_up():
    started = time.perf_counter()
    thoughts = OpenSpielMCTSAgent(seed=0, time_limit=0.05).think(Position.start())

    assert time.perf_counter() - started < 0.5
    assert thoughts.playouts > 100  # written in C++, it plays thousands of playouts per second


def test_make_agent_builds_openspiel_agents():
    mcts, alphabeta = make_agent("OpenSpielMCTS:500"), make_agent("OpenSpielAlphaBeta:4:mix")

    assert (mcts.playouts, mcts.time_limit) == (500, None)
    assert (alphabeta.depth, alphabeta.heuristic) == (4, HEURISTICS["mix"])
    assert make_agent("OpenSpielMCTS").time_limit == 0.1
    assert make_agent("OpenSpielAlphaBeta").depth == 6
    with pytest.raises(ValueError):
        make_agent("OpenSpielMCTS:mix")


@pytest.mark.parametrize("name", ["OpenSpielMCTS:100", "OpenSpielAlphaBeta:2"])
def test_wins_a_small_tournament_against_random(name):
    # The tournament starts every game with random moves, then lets the agents play: OpenSpiel follows all of them.
    tournament = run_tournament(name, "Random", openings=2, opening_moves=6, seed=1, workers=1)

    assert tournament.points() == [1.0] * 4
