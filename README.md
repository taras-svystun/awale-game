# Awalé

Awalé (Oware) on your own computer: play against a friend or an AI, and build AI players and compare them.
No internet and no server needed.

The rules we use and the words we use for them are in [CONTEXT.md](CONTEXT.md). The roadmap is in [docs/PLAN.md](docs/PLAN.md).

## First-time setup

Needs Python 3.11 or newer. Run this once, from the project folder:

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Run the second line again after pulling new code, in case new packages were added.

## Play

```sh
.venv/bin/awale play
```

A start menu opens first. For South and for North, pick Person or an AI agent (only Random for now), pick who moves first, and press Start or Enter.
Two people can share the computer, or you can play against an AI. To play on a real wooden board against the AI, set your friend as the Person, type in their moves, and copy the AI's moves onto the board: the line under the title says which pit the AI played.

South sits at the bottom and North at the top. Click a pit in your row, or press 1-6 to play your pit counted from your own left (North's pit 1 is at the top right).
Pits you cannot play are dimmed. The orange ring shows the last move.

Keys: U or Backspace undoes (one move between two people, or back to your last turn against an AI), N starts a new game with the same players, M goes back to the menu, Esc quits.

## Run the tests

```sh
.venv/bin/pytest
```

This also plays 2000 random games in our engine and in OpenSpiel side by side, to check that our rules are right. It takes about 5 seconds.

Only the quick rule tests, without OpenSpiel:

```sh
.venv/bin/pytest tests/test_position.py tests/test_game.py
```

Only the Random agent's tests:

```sh
.venv/bin/pytest tests/test_random_agent.py
```

## Try the engine in Python

You can also play without a window, in a Python shell:

```sh
.venv/bin/python
```

```python
from awale.engine import Game, Side

game = Game(first=Side.SOUTH)
game.position.legal_moves()      # [1, 2, 3, 4, 5, 6]
game.play(3)                     # South sows from its pit 3
game.position.pits(Side.NORTH)   # (5, 4, 4, 4, 4, 4), from North's own left
game.undo()
```
