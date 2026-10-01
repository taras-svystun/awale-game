"""Rules every agent follows, whatever its algorithm."""

import subprocess
import sys

import pytest

from awale.agents import HEURISTICS, Agent, GreedyAgent, MinimaxAgent, RandomAgent, Thoughts, make_agent
from awale.engine import Position


def test_agents_never_import_pygame():
    # The engine and the agents must work without a window, e.g. in a tournament or a web version.
    code = "import sys, awale.agents; print('pygame' in sys.modules)"
    output = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout

    assert output.strip() == "False"


def test_an_agent_that_only_chooses_a_move_thinks_with_no_scores():
    thoughts = RandomAgent(seed=1).think(Position.start())

    assert thoughts.move in range(1, 7)
    assert thoughts.scores == {}
    assert thoughts.line == ()


def test_an_agent_that_only_thinks_can_also_just_choose_a_move():
    class ThinkingAgent(Agent):
        def think(self, position):
            return Thoughts(move=4, scores={4: 1.0, 5: 0.0})

    assert ThinkingAgent().choose_move(Position.start()) == 4


def test_an_agent_must_write_choose_move_or_think():
    with pytest.raises(TypeError, match="choose_move or think"):

        class EmptyAgent(Agent):
            pass


def test_make_agent_builds_an_agent_by_its_name():
    agent = make_agent("Greedy", seed=1)

    assert isinstance(agent, GreedyAgent)
    assert agent.name == "Greedy"


def test_make_agent_sets_the_depth_of_a_search_agent():
    default, deep = make_agent("Minimax"), make_agent("Minimax:6")

    assert isinstance(deep, MinimaxAgent)
    assert (default.depth, deep.depth) == (4, 6)
    assert deep.name == "Minimax:6"  # shown in the window and written in game records


def test_make_agent_sets_the_heuristic_of_a_search_agent():
    default, store, deep = make_agent("AlphaBeta"), make_agent("AlphaBeta:store"), make_agent("AlphaBeta:8:store")

    assert default.heuristic is store.heuristic is deep.heuristic is HEURISTICS["store"]
    assert (store.depth, deep.depth) == (6, 8)
    assert make_agent("AlphaBeta:store:8").depth == 8  # any order


@pytest.mark.parametrize(
    "name",
    [
        "Nobody",
        "Greedy:3",
        "Greedy:store",
        "Minimax:0",
        "Minimax:deep",
        "Minimax:",
        "Minimax:3:4",
        "Minimax:store:store",
        "Minimax:1s",
    ],
)
def test_make_agent_refuses_a_name_it_does_not_know(name):
    with pytest.raises(ValueError):
        make_agent(name)


def test_make_agent_says_what_an_agent_can_set():
    with pytest.raises(ValueError, match="Greedy has nothing to set"):
        make_agent("Greedy:3")
    with pytest.raises(ValueError, match="is not a number of playouts .* nor a time limit"):
        make_agent("MCTS:mix")
