"""Rules every agent follows, whatever its algorithm."""

import subprocess
import sys

import pytest

from awale.agents import Agent, RandomAgent, Thoughts
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
