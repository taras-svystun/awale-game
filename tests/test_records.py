"""Game records: move letters, saving, loading and replaying games."""

import json

import pytest

from awale import records
from awale.agents import RandomAgent
from awale.engine import Game, Position, Side
from awale.records import GameRecord, load_game, move_letter, new_record_file, read_move_letter, save_game


def random_game(first=Side.SOUTH, seed=0) -> Game:
    game = Game(first=first)
    agent = RandomAgent(seed)
    while not game.is_over:
        game.play(agent.choose_move(game.position))
    return game


def test_move_letters_are_lower_case_for_south_and_upper_case_for_north():
    assert [move_letter(Side.SOUTH, pit) for pit in range(1, 7)] == list("abcdef")
    assert [move_letter(Side.NORTH, pit) for pit in range(1, 7)] == list("ABCDEF")
    assert read_move_letter("c") == (Side.SOUTH, 3)
    assert read_move_letter("D") == (Side.NORTH, 4)


def test_a_record_writes_each_move_for_the_player_who_made_it():
    game = Game()
    game.play(3)  # South's pit 3
    game.play(4)  # North's pit 4
    while not game.is_over:
        game.play(game.position.legal_moves()[0])

    record = GameRecord.of(game, "Person", "Random")

    assert record.moves[:2] == ("c", "D")
    assert (record.winner, record.score) == (game.result.winner, game.result.score)


def test_replaying_a_record_gives_the_same_game():
    for first in Side:
        game = random_game(first)

        replayed = GameRecord.of(game, "Random", "Random").replay()

        assert replayed.positions == game.positions
        assert replayed.result == game.result


def test_only_finished_games_from_the_start_position_can_be_recorded():
    unfinished = Game()
    unfinished.play(1)
    set_up = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4), stores=(23, 0)))
    set_up.play(6)

    with pytest.raises(ValueError):
        GameRecord.of(unfinished, "Person", "Person")
    with pytest.raises(ValueError):
        GameRecord.of(set_up, "Person", "Person")


def test_a_saved_game_loads_back_the_same(records_in_a_temporary_folder):
    record = GameRecord.of(random_game(), "Person", "Random")

    path = save_game(record)

    assert path.parent == records_in_a_temporary_folder / "games"
    assert load_game(path) == record
    data = json.loads(path.read_text())
    assert data["south"] == "Person"
    assert data["moves"] == " ".join(record.moves)  # easy to read in the file


def test_only_the_newest_records_are_kept(tmp_path):
    folder = tmp_path / "some records"
    for i in range(5):
        new_record_file(folder, f"{i}.txt", keep=3).write_text(str(i))

    assert [path.read_text() for path in sorted(folder.iterdir())] == ["2", "3", "4"]


def test_save_game_keeps_the_last_100_games(monkeypatch, records_in_a_temporary_folder):
    monkeypatch.setattr(records, "KEEP_GAMES", 3)
    record = GameRecord.of(random_game(), "Random", "Random")

    for _ in range(5):
        save_game(record)

    assert len(list((records_in_a_temporary_folder / "games").iterdir())) == 3
