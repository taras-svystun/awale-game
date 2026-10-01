"""The MCTS agent: many random games to the end, and more of them after the moves that look good."""

import time

import pytest

from awale.agents import MCTSAgent, RandomAgent, make_agent
from awale.agents.mcts_agent import Node, points
from awale.engine import Position, Side
from awale.tournament import run_tournament
from test_alphabeta_agent import GREEDY_TRAP, play_whole_game, some_positions
from test_deepening_agent import ENDINGS


def all_nodes(node):
    yield node
    for child in node.children:
        yield from all_nodes(child)


def test_every_playout_goes_through_the_top_and_adds_one_position():
    position = GREEDY_TRAP
    root = MCTSAgent(seed=0, playouts=500).grow_tree(position)

    assert root.visits == 500
    assert sorted(child.move for child in root.children) == position.legal_moves()
    assert sum(child.visits for child in root.children) == 500
    for node in all_nodes(root):
        assert 0 <= node.wins <= node.visits
        if node is not root and not node.position.ends_game():
            # One playout started here when the node was added, and every later one went on to a child.
            assert node.visits == 1 + sum(child.visits for child in node.children)


def test_the_same_seed_gives_the_same_thoughts():
    for position in some_positions(5):
        assert MCTSAgent(seed=3, playouts=200).think(position) == MCTSAgent(seed=3, playouts=200).think(position)


def test_its_thoughts():
    thoughts = MCTSAgent(seed=0, playouts=300).think(Position.start())

    assert thoughts.playouts == 300
    assert list(thoughts.scores) == [1, 2, 3, 4, 5, 6]
    assert all(0 <= score <= 1 for score in thoughts.scores.values())  # a share of wins
    assert thoughts.line[0] == thoughts.move
    assert thoughts.depth >= len(thoughts.line)
    assert thoughts.positions > 300 * 20  # every playout plays many moves to the end


def test_plays_the_move_it_tried_most():
    # The same seed grows the same tree, so we can look at the tree `think` grew.
    root = MCTSAgent(seed=0, playouts=300).grow_tree(GREEDY_TRAP)
    thoughts = MCTSAgent(seed=0, playouts=300).think(GREEDY_TRAP)

    most = max(root.children, key=lambda child: child.visits)
    assert thoughts.move == most.move
    assert thoughts.scores[most.move] == most.win_share


def test_the_expected_line_follows_the_answers_tried_most():
    thoughts = MCTSAgent(seed=0, playouts=1000).think(GREEDY_TRAP)
    root = MCTSAgent(seed=0, playouts=1000).grow_tree(GREEDY_TRAP)

    node = root
    for move in thoughts.line:
        node = next(child for child in node.children if child.move == move)
        assert node.visits >= 2
        if node.parent is not root:
            assert node.visits == max(child.visits for child in node.parent.children)


def test_selection_prefers_good_moves_but_tries_the_others_now_and_then():
    parent = Node(Position.start())
    parent.visits = 100
    good, rare = Node(Position.start(), move=1, parent=parent), Node(Position.start(), move=2, parent=parent)
    good.visits, good.wins = 90, 54  # won 60% of 90 playouts
    rare.visits, rare.wins = 10, 4  # won 40% of only 10 playouts
    parent.children = [good, rare]

    # With no bonus for trying, it only looks at the share of wins.
    assert MCTSAgent(exploration=0).select(parent) is good
    # With the bonus: 0.60 + 1.41 * sqrt(ln 100 / 90) = 0.92 for the good move,
    # and 0.40 + 1.41 * sqrt(ln 100 / 10) = 1.36 for the rare one. The rare one is tried again.
    assert MCTSAgent().select(parent) is rare


def test_a_playout_goes_to_the_end_of_the_game():
    end = MCTSAgent(seed=0).playout(Position.start())

    assert end.board == (0,) * 12  # the seeds left on the board were collected
    assert sum(end.stores) == 48


def test_points_for_a_win_a_draw_and_a_loss():
    end = Position.setup(south=(0,) * 6, north=(0,) * 6, stores=(30, 18))

    assert (points(end, Side.SOUTH), points(end, Side.NORTH)) == (1, 0)
    assert points(Position.setup(south=(0,) * 6, north=(0,) * 6, stores=(24, 24)), Side.SOUTH) == 0.5


def test_takes_a_win_in_one_move():
    # South has 23, and its pit 6 captures 2 from North's pit 1.
    assert MCTSAgent(seed=0, playouts=200).think(ENDINGS[0]).move == 6


@pytest.mark.parametrize("seed", range(3))
def test_does_not_fall_into_the_greedy_trap(seed):
    # The position from docs/agents/greedy.md: pit 2 captures 2 but gives away 5, pit 6 captures 2 safely.
    assert MCTSAgent(seed=seed, playouts=1000).think(GREEDY_TRAP).move == 6


def test_stops_when_the_time_is_up():
    started = time.perf_counter()
    thoughts = MCTSAgent(seed=0, time_limit=0.05).think(Position.start())
    seconds = time.perf_counter() - started

    assert seconds < 0.05 + 0.02  # one playout more takes about 1 ms
    assert thoughts.playouts > 20


def test_even_with_almost_no_time_it_tries_every_move_once():
    thoughts = MCTSAgent(seed=0, time_limit=0.000001).think(GREEDY_TRAP)

    assert thoughts.playouts == 5
    assert list(thoughts.scores) == GREEDY_TRAP.legal_moves()


def test_plays_whole_games():
    moves = play_whole_game(MCTSAgent(seed=0, playouts=20), RandomAgent(seed=1))

    assert len(moves) > 10


def test_beats_random_in_a_small_tournament():
    tournament = run_tournament("MCTS:30", "Random", openings=2, seed=0, workers=1)

    assert tournament.points() == [1, 1, 1, 1]  # all 4 games won


def test_thinks_for_a_tenth_of_a_second_unless_told_otherwise():
    agent = make_agent("MCTS")

    assert (agent.playouts, agent.time_limit) == (None, 0.1)


def test_make_agent_sets_the_playouts_a_time_limit_or_both():
    assert (make_agent("MCTS:1000").playouts, make_agent("MCTS:1000").time_limit) == (1000, None)
    assert (make_agent("MCTS:0.5s").playouts, make_agent("MCTS:0.5s").time_limit) == (None, 0.5)

    both = make_agent("MCTS:2s:500")  # any order
    assert (both.playouts, both.time_limit) == (500, 2.0)
    assert both.name == "MCTS:2s:500"


@pytest.mark.parametrize("name", ["MCTS:0", "MCTS:mix", "MCTS:100:200", "MCTS:1s:2s", "MCTS:0s", "MCTS:deep"])
def test_make_agent_refuses_what_mcts_cannot_use(name):
    with pytest.raises(ValueError):
        make_agent(name)


def test_needs_at_least_1_playout_and_a_time_above_0():
    with pytest.raises(ValueError, match="MCTS needs at least 1 playout"):
        MCTSAgent(playouts=0)
    with pytest.raises(ValueError, match="MCTS needs a time limit"):
        MCTSAgent(time_limit=0)
