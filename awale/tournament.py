"""Tournament: many games between two AI agents, with no window, to compare them with numbers.

Each random opening is played twice, with the agents swapping sides, so neither agent
gets the luckier openings or the better side more often than the other.
Games are spread over all CPU cores, one process per core.
"""

import csv
import math
import os
import random
import statistics
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from awale import records
from awale.agents import make_agent
from awale.engine import Game, Side
from awale.records import GameRecord

OPENINGS = 500
OPENING_MOVES = 6
# 95% of the time, the true average is within 1.96 standard errors of the average we measured.
Z_95 = 1.96


@dataclass(frozen=True)
class GameJob:
    """Everything a worker process needs to play one tournament game."""

    number: int  # 1, 2, 3, ...
    opening: tuple[int, ...]  # pits played at random from the start position
    a_side: Side  # the side agent A plays in this game
    south: str  # agent names for make_agent, like "Greedy" or "Minimax:6"
    north: str
    south_seed: int
    north_seed: int


@dataclass(frozen=True)
class GameOutcome:
    job: GameJob
    record: GameRecord  # the whole game, opening included
    thinking: tuple[float, float]  # seconds spent in choose_move, (South, North)
    agent_moves: tuple[int, int]  # moves chosen by each agent, not counting the opening, (South, North)


def play_game(job: GameJob) -> GameOutcome:
    """Play one game. Runs in a worker process, so it builds its own agents from their names."""
    agents = {Side.SOUTH: make_agent(job.south, job.south_seed), Side.NORTH: make_agent(job.north, job.north_seed)}
    game = Game()
    for pit in job.opening:
        game.play(pit)
    thinking = {Side.SOUTH: 0.0, Side.NORTH: 0.0}
    agent_moves = {Side.SOUTH: 0, Side.NORTH: 0}
    while not game.is_over:
        side = game.position.to_move
        started = time.perf_counter()
        pit = agents[side].choose_move(game.position)
        thinking[side] += time.perf_counter() - started
        agent_moves[side] += 1
        game.play(pit)
    record = GameRecord.of(game, job.south, job.north)
    return GameOutcome(job, record, (thinking[Side.SOUTH], thinking[Side.NORTH]), (agent_moves[Side.SOUTH], agent_moves[Side.NORTH]))


def random_openings(count: int, length: int, rng: random.Random) -> list[tuple[int, ...]]:
    """`count` different openings of `length` random legal moves from the start, none of which ends the game."""
    openings: dict[tuple[int, ...], None] = {}  # a dict keeps the order, and skips repeats like a set
    for _ in range(count * 100):
        if len(openings) == count:
            break
        game = Game()
        while len(game.moves) < length and not game.is_over:
            game.play(rng.choice(game.position.legal_moves()))
        if not game.is_over:
            openings[tuple(game.moves)] = None
    if len(openings) < count:
        raise ValueError(f"Could not find {count} different openings of {length} moves. Use longer openings.")
    return list(openings)


def make_jobs(a: str, b: str, openings: int, opening_moves: int, seed: int | None) -> list[GameJob]:
    """Two games per opening: A plays South in the first and North in the second."""
    rng = random.Random(seed)
    jobs = []
    for opening in random_openings(openings, opening_moves, rng):
        for a_side in Side:
            south, north = (a, b) if a_side is Side.SOUTH else (b, a)
            # Made here, not in the workers, so the same seed always gives the same games.
            seeds = rng.getrandbits(32), rng.getrandbits(32)
            jobs.append(GameJob(len(jobs) + 1, opening, a_side, south, north, *seeds))
    return jobs


@dataclass(frozen=True)
class Tournament:
    a: str
    b: str
    opening_moves: int
    outcomes: list[GameOutcome]

    def points(self) -> list[float]:
        """Agent A's points in each game: 1 for a win, 1/2 for a draw, 0 for a loss. B gets the rest."""
        points = []
        for outcome in self.outcomes:
            winner = outcome.record.winner
            points.append(0.5 if winner is None else 1.0 if winner is outcome.job.a_side else 0.0)
        return points

    def seed_differences(self) -> list[int]:
        """In each game, the seeds A ended with minus the seeds B ended with."""
        differences = []
        for outcome in self.outcomes:
            south, north = outcome.record.score
            differences.append(south - north if outcome.job.a_side is Side.SOUTH else north - south)
        return differences

    def seconds_per_move(self, agent: str) -> float:
        """Average time agent "a" or "b" spent choosing one move."""
        thinking = moves = 0
        for outcome in self.outcomes:
            side = outcome.job.a_side if agent == "a" else outcome.job.a_side.opponent
            index = side.value
            thinking += outcome.thinking[index]
            moves += outcome.agent_moves[index]
        return thinking / moves if moves else 0.0

    def report(self) -> str:
        games = len(self.outcomes)
        points = self.points()
        wins, draws = points.count(1.0), points.count(0.5)
        losses = games - wins - draws
        share, share_margin = mean_and_margin(points)
        difference, difference_margin = mean_and_margin(self.seed_differences())
        winners = [outcome.record.winner for outcome in self.outcomes]

        low, high = share - share_margin, share + share_margin
        if low > 0.5:
            verdict = f"A ({self.a}) is stronger: its whole interval is above 50%."
        elif high < 0.5:
            verdict = f"B ({self.b}) is stronger: A's whole interval is below 50%."
        else:
            verdict = "The interval includes 50%, so these games cannot tell the two agents apart."

        return "\n".join(
            [
                f"A: {self.a}    B: {self.b}",
                f"{games} games: {games // 2} random openings of {self.opening_moves} moves, "
                "each played twice with the agents swapping sides.",
                "",
                f"A wins {wins} ({percent(wins / games)}), draws {draws} ({percent(draws / games)}), "
                f"loses {losses} ({percent(losses / games)}).",
                f"A's points: {percent(share)} ± {percent(share_margin)}  "
                "(a win is 1 point, a draw 1/2; 95% confidence interval)",
                f"Seeds at the end, A minus B: {difference:+.1f} ± {difference_margin:.1f} on average.",
                f"Time per move: A {duration(self.seconds_per_move('a'))}, B {duration(self.seconds_per_move('b'))}.",
                f"By side: South won {winners.count(Side.SOUTH)}, North won {winners.count(Side.NORTH)}, "
                f"{winners.count(None)} draws.",
                "",
                verdict,
            ]
        )

    def save(self) -> Path:
        """Write one CSV row per game in records/tournaments, keeping only the newest KEEP_TOURNAMENTS."""
        folder = records.RECORDS_DIR / "tournaments"
        path = records.new_record_file(folder, f"{self.a}-vs-{self.b}.csv", records.KEEP_TOURNAMENTS)
        with path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["game", "south", "north", "a_plays", "winner", "south_seeds", "north_seeds",
                 "moves", "south_ms_per_move", "north_ms_per_move", "opening", "record"]
            )  # fmt: skip
            for outcome in self.outcomes:
                job, record = outcome.job, outcome.record
                ms_per_move = [
                    f"{seconds / moves * 1000:.3f}" if moves else ""
                    for seconds, moves in zip(outcome.thinking, outcome.agent_moves)
                ]
                writer.writerow(
                    [job.number, job.south, job.north, job.a_side.name.title(),
                     record.winner.name.title() if record.winner else "Draw", *record.score,
                     len(record.moves), *ms_per_move,
                     " ".join(record.moves[: len(job.opening)]), " ".join(record.moves)]
                )  # fmt: skip
        return path


def run_tournament(
    a: str,
    b: str,
    openings: int = OPENINGS,
    opening_moves: int = OPENING_MOVES,
    seed: int | None = None,
    workers: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Tournament:
    """Play agent A against agent B (names for make_agent, like "Greedy" or "Minimax:6"): two games per random opening.

    `workers` is the number of processes, all CPU cores by default. With 1, everything runs here.
    `on_progress(done, total)` is called after each game.
    """
    jobs = make_jobs(a, b, openings, opening_moves, seed)
    outcomes = []
    for outcome in play_all(jobs, workers or os.cpu_count() or 1):
        outcomes.append(outcome)
        if on_progress:
            on_progress(len(outcomes), len(jobs))
    return Tournament(a, b, opening_moves, outcomes)


def play_all(jobs: list[GameJob], workers: int) -> Iterator[GameOutcome]:
    """Play the games in `workers` processes, and give back their outcomes in the same order as the jobs."""
    if workers == 1:
        yield from map(play_game, jobs)
        return
    with ProcessPoolExecutor(workers) as executor:
        # Send the games in small batches: one at a time would spend more time talking than playing.
        chunk = max(1, len(jobs) // (workers * 10))
        yield from executor.map(play_game, jobs, chunksize=chunk)


def mean_and_margin(values: list[float]) -> tuple[float, float]:
    """The average, and how far the true average may be from it (95% confidence).

    The margin is 1.96 standard errors: the spread of the values divided by the square root
    of how many there are. Four times more games make the margin two times smaller.
    """
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, math.inf
    return mean, Z_95 * statistics.stdev(values) / math.sqrt(len(values))


def percent(share: float) -> str:
    return f"{share * 100:.1f}%"


def duration(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} µs"
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.2f} s"
