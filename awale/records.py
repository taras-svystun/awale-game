"""Game records: saved games, and where they are kept. No Pygame here.

A move is written as one letter: a-f for South's pits 1-6, A-F for North's pits 1-6.
So "c D" means South sowed from its pit 3, then North from its pit 4.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from awale.engine import Game, Position, Side

# The `records` folder next to the `awale` package, i.e. in the project folder. Git ignores it.
RECORDS_DIR = Path(__file__).resolve().parent.parent / "records"
KEEP_GAMES = 100
KEEP_TOURNAMENTS = 10


def move_letter(side: Side, pit: int) -> str:
    letter = "abcdef"[pit - 1]
    return letter if side is Side.SOUTH else letter.upper()


def read_move_letter(letter: str) -> tuple[Side, int]:
    """The opposite of `move_letter`: "c" is (South, 3), "D" is (North, 4)."""
    pit = "abcdef".index(letter.lower()) + 1
    return (Side.SOUTH if letter.islower() else Side.NORTH), pit


@dataclass(frozen=True)
class GameRecord:
    """A finished game: who played each side, the moves, and the result."""

    south: str  # the agent's name, or "Person"
    north: str
    moves: tuple[str, ...]  # move letters, like ("c", "D", "a")
    winner: Side | None  # None means a draw
    score: tuple[int, int]  # seeds at the end, (South, North)

    @classmethod
    def of(cls, game: Game, south: str, north: str) -> "GameRecord":
        if game.result is None:
            raise ValueError("Only a finished game can be recorded")
        if game.positions[0] != Position.start(game.positions[0].to_move):
            raise ValueError("Only a game from the start position can be recorded: its moves alone must tell the game")
        # positions[k] is the position before move k, so it knows who made that move.
        movers = [position.to_move for position in game.positions]
        moves = tuple(move_letter(side, pit) for side, pit in zip(movers, game.moves))
        return cls(south, north, moves, game.result.winner, game.result.score)

    def replay(self) -> Game:
        """Play the moves again in a new game, so you can look at any position of it."""
        first = read_move_letter(self.moves[0])[0] if self.moves else Side.SOUTH
        game = Game(first=first)
        for letter in self.moves:
            side, pit = read_move_letter(letter)
            if side is not game.position.to_move:
                raise ValueError(f"Move {letter} is {side.name}'s, but {game.position.to_move.name} is to move")
            game.play(pit)
        return game

    def to_dict(self) -> dict:
        return {
            "south": self.south,
            "north": self.north,
            "moves": " ".join(self.moves),
            "winner": self.winner.name.title() if self.winner else "Draw",
            "score": list(self.score),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameRecord":
        winner = None if data["winner"] == "Draw" else Side[data["winner"].upper()]
        south, north = data["score"]
        return cls(data["south"], data["north"], tuple(data["moves"].split()), winner, (south, north))


def save_game(record: GameRecord) -> Path:
    """Save a Play or Watch game in records/games, keeping only the newest KEEP_GAMES."""
    path = new_record_file(RECORDS_DIR / "games", f"{record.south}-vs-{record.north}.json", KEEP_GAMES)
    data = {"played_at": datetime.now().isoformat(timespec="seconds"), **record.to_dict()}
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def load_game(path: Path) -> GameRecord:
    return GameRecord.from_dict(json.loads(Path(path).read_text()))


def new_record_file(folder: Path, name: str, keep: int) -> Path:
    """A path for a new file in `folder`, named by the time now so the files sort from old to new.

    Deletes the oldest files so that, with the new one, at most `keep` are left.
    """
    folder.mkdir(parents=True, exist_ok=True)
    old = sorted(folder.iterdir())
    for path in old[: max(0, len(old) - keep + 1)]:
        path.unlink()
    return folder / f"{datetime.now():%Y-%m-%d_%H-%M-%S-%f}_{name}"

