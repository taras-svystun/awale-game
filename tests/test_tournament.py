"""Tournament: random openings, fair side swapping, the numbers in the report, and the CSV."""

import csv
import random
import subprocess
import sys
import time
from pathlib import Path

import pytest

from awale import agents, records
from awale.agents import Agent
from awale.engine import Game, Side
from awale.records import GameRecord
from awale.tournament import make_jobs, mean_and_margin, random_openings, run_tournament


class CaptureAgent(Agent):
    """A test agent that plays the move capturing the most seeds. It should beat Random clearly."""

    name = "Capture"

    def choose_move(self, position):
        me = position.to_move
        return max(position.legal_moves(), key=lambda pit: position.play(pit).store(me))


class SlowAgent(Agent):
    """A test agent that takes 2 ms per move, to check the time per move."""

    name = "Slow"

    def choose_move(self, position):
        time.sleep(0.002)
        return position.legal_moves()[0]


@pytest.fixture(autouse=True)
def test_agents(monkeypatch):
    # Only for games in this process (workers=1): other processes do not see these agents.
    monkeypatch.setitem(agents.AGENTS, "Capture", CaptureAgent)
    monkeypatch.setitem(agents.AGENTS, "Slow", SlowAgent)


def test_openings_are_different_and_none_ends_the_game():
    openings = random_openings(200, 6, random.Random(0))

    assert len(set(openings)) == 200
    for opening in openings:
        game = Game()
        for pit in opening:
            game.play(pit)
        assert len(opening) == 6 and not game.is_over


def test_each_opening_is_played_twice_with_the_agents_swapping_sides():
    jobs = make_jobs("Capture", "Random", openings=10, opening_moves=6, seed=0)

    assert len(jobs) == 20
    assert [job.number for job in jobs] == list(range(1, 21))
    for first, second in zip(jobs[::2], jobs[1::2]):
        assert first.opening == second.opening
        assert (first.a_side, first.south, first.north) == (Side.SOUTH, "Capture", "Random")
        assert (second.a_side, second.south, second.north) == (Side.NORTH, "Random", "Capture")


def test_random_against_random_is_about_even():
    tournament = run_tournament("Random", "Random", openings=300, seed=0, workers=1)

    share, margin = mean_and_margin(tournament.points())
    assert len(tournament.outcomes) == 600
    assert share - margin < 0.5 < share + margin
    assert "cannot tell the two agents apart" in tournament.report()


def test_a_stronger_agent_wins_whichever_side_it_is():
    as_a = run_tournament("Capture", "Random", openings=50, seed=0, workers=1)
    as_b = run_tournament("Random", "Capture", openings=50, seed=0, workers=1)

    assert mean_and_margin(as_a.points())[0] > 0.8
    assert mean_and_margin(as_b.points())[0] < 0.2
    assert sum(as_a.seed_differences()) > 0
    assert "A (Capture) is stronger" in as_a.report()
    assert "B (Capture) is stronger" in as_b.report()


def test_the_same_seed_plays_the_same_games():
    def moves(seed):
        return [outcome.record.moves for outcome in run_tournament("Random", "Random", 20, seed=seed, workers=1).outcomes]

    assert moves(1) == moves(1)
    assert moves(1) != moves(2)


def test_many_processes_give_the_same_games_as_one():
    one = run_tournament("Random", "Random", openings=20, seed=5, workers=1)
    two = run_tournament("Random", "Random", openings=20, seed=5, workers=2)

    assert [o.record for o in one.outcomes] == [o.record for o in two.outcomes]


def test_time_per_move_is_measured_for_each_agent():
    tournament = run_tournament("Slow", "Random", openings=1, seed=0, workers=1)

    assert tournament.seconds_per_move("a") >= 0.002
    assert tournament.seconds_per_move("b") < 0.001


def test_progress_is_reported_after_each_game():
    calls = []

    run_tournament("Random", "Random", openings=3, seed=0, workers=1, on_progress=lambda *call: calls.append(call))

    assert calls == [(1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6)]


def test_a_saved_tournament_has_one_csv_row_per_game(records_in_a_temporary_folder):
    tournament = run_tournament("Capture", "Random", openings=5, seed=0, workers=1)

    path = tournament.save()

    assert path.parent == records_in_a_temporary_folder / "tournaments"
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 10
    for row, outcome in zip(rows, tournament.outcomes):
        record = GameRecord(row["south"], row["north"], tuple(row["record"].split()), outcome.record.winner, outcome.record.score)
        game = record.replay()  # the moves in the CSV are the whole game
        assert row["winner"] == (game.result.winner.name.title() if game.result.winner else "Draw")
        assert row["record"].startswith(row["opening"])


def test_only_the_last_10_tournaments_are_kept(monkeypatch, records_in_a_temporary_folder):
    monkeypatch.setattr(records, "KEEP_TOURNAMENTS", 2)
    tournament = run_tournament("Random", "Random", openings=1, seed=0, workers=1)

    for _ in range(4):
        tournament.save()

    assert len(list((records_in_a_temporary_folder / "tournaments").iterdir())) == 2


def test_the_tournament_command_prints_the_report():
    awale = Path(sys.executable).parent / "awale"

    result = subprocess.run(
        [awale, "tournament", "Random", "Random", "--openings", "5", "--seed", "1", "--workers", "1"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip

    assert "10 games: 5 random openings of 6 moves" in result.stdout
    assert "A's points:" in result.stdout
    assert "Played 10 of 10 games" in result.stderr


def test_the_tournament_command_takes_a_search_depth():
    awale = Path(sys.executable).parent / "awale"

    result = subprocess.run(
        [awale, "tournament", "Minimax:2", "Greedy", "--openings", "2", "--seed", "1", "--workers", "1"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip

    assert "A: Minimax:2    B: Greedy" in result.stdout


def test_the_tournament_command_refuses_an_unknown_agent_before_playing():
    awale = Path(sys.executable).parent / "awale"

    result = subprocess.run([awale, "tournament", "Greedy:3", "Random"], capture_output=True, text=True)

    assert result.returncode != 0
    assert "Greedy has nothing to set" in result.stderr
