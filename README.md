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

A start menu opens first. For South and for North, pick Person or an AI agent (Random, Greedy, Minimax, AlphaBeta, AlphaBeta:mix or Deepening:mix, see [AI agents](#ai-agents)), pick who moves first, and press Start or Enter.
Two people can share the computer, or you can play against an AI. If you pick an AI agent on both sides, Start opens [Watch](#watch) instead. To play on a real wooden board against the AI, set your friend as the Person, type in their moves, and copy the AI's moves onto the board: the line under the title says which pit the AI played.

South sits at the bottom and North at the top. Click a pit in your row, or press 1-6 to play your pit counted from your own left (North's pit 1 is at the top right).
Pits you cannot play are dimmed. The orange ring shows the last move.

Keys: U or Backspace undoes (one move between two people, or back to your last turn against an AI), N starts a new game with the same players, M goes back to the menu, Esc quits.

Every finished game is saved as a game record in `records/games` (see [Game records](#game-records) below).

## Watch

Watch two AI agents play each other, move by move, with their thoughts next to the board:

```sh
.venv/bin/awale watch Random Random
```

The first name plays South (at the bottom), the second North (at the top). South moves first; to let North move first:

```sh
.venv/bin/awale watch Random Random --first north
```

You can also get here from the start menu of `awale play`: pick an AI agent for both South and North, then Start.

Each agent first thinks about the position on the board and shows its thoughts, then plays its move after a short wait.

- Pause (Space or P) stops the game; press it again to go on.
- Step (S or the right arrow) pauses and plays just the next move.
- Speed: drag the knob from 3 seconds per move (left) to 0.1 seconds per move (right).
- The thoughts panel has a checkbox for each part:
  - Move scores: a score over each pit the agent may play, higher is better for it. Its choice is in yellow.
  - Expected line: the moves it expects next, in move letters (a-f South, A-F North).
  - Work done: how many positions it looked at, how many moves ahead, and how long it took.

Random does not look ahead, so it has no scores and no line, and its work is 0 positions. Greedy shows the seeds each move would capture:

```sh
.venv/bin/awale watch Greedy Random
```

Minimax shows how good each move is after looking 4 moves ahead, and the line of play it expects:

```sh
.venv/bin/awale watch Minimax Greedy
```

Put a depth after a colon to make Minimax look further ahead (or less far). Depth 6 takes up to about 0.2 seconds per move:

```sh
.venv/bin/awale watch Minimax:6 Minimax:2
```

AlphaBeta shows the same scores and the same line as Minimax at the same depth, but looks at far fewer positions (see "Work done"). Compare the two side by side:

```sh
.venv/bin/awale watch AlphaBeta:4 Minimax
```

AlphaBeta looks 6 moves ahead unless you give it a depth, and is still quick at 8:

```sh
.venv/bin/awale watch AlphaBeta:8 AlphaBeta
```

Put a heuristic's name after a colon to change how an agent judges the positions where it stops looking (see [Heuristics](#heuristics)). `AlphaBeta:mix` gives moves different scores where plain AlphaBeta sees them all the same:

```sh
.venv/bin/awale watch AlphaBeta:mix AlphaBeta
```

Deepening looks deeper and deeper until its time is up, 0.1 seconds per move unless you give it another time (see [AI agents](#ai-agents)). "Work done" shows how deep it got. It proves most moves worse than its choice without their exact score: those scores have a "≤" in front, meaning "this or less":

```sh
.venv/bin/awale watch Deepening:mix AlphaBeta:mix
```

Give it more time with a number of seconds and an "s". With 1 second per move it looks about 12 moves ahead:

```sh
.venv/bin/awale watch Deepening:1s:mix Deepening:mix
```

Keys: N starts a new game with the same agents, M goes back to the menu, Esc quits.
Every finished Watch game is saved as a game record too.

## AI agents

Each agent is explained in its own file in [docs/agents](docs/agents):

- **Random** ([random.md](docs/agents/random.md)): plays any legal move. The baseline.
- **Greedy** ([greedy.md](docs/agents/greedy.md)): plays the move that captures the most seeds right now. Beats Random in about 93% of the points.
- **Minimax** ([minimax.md](docs/agents/minimax.md)): looks 4 moves ahead and expects the opponent to answer with their best move. It judges where it stops by the seeds each player has captured. `Minimax:6` looks 6 moves ahead, `Minimax:2` only 2. Even `Minimax:2` beats Greedy in 99% of the points.
- **AlphaBeta** ([alphabeta.md](docs/agents/alphabeta.md)): Minimax that skips the lines of play that cannot change its choice. It chooses exactly the same moves as Minimax at the same depth, only much faster, so it can look 6 moves ahead by default. `AlphaBeta:8` looks 8 moves ahead.
- **Deepening** ([deepening.md](docs/agents/deepening.md)): AlphaBeta that tries the most promising moves first and looks 1, 2, 3, ... moves ahead until its time is up. By default it thinks for 0.1 seconds per move. Give it a time, a depth, or both, and it stops at whichever comes first:
  - `Deepening:0.5s` thinks for half a second per move;
  - `Deepening:8` always looks 8 moves ahead, with no time limit. It then chooses exactly the moves `AlphaBeta:8` chooses, only faster;
  - `Deepening:12:1s` stops at 12 moves ahead or after 1 second.

In the start menu, Minimax always looks 4 moves ahead and AlphaBeta 6, AlphaBeta:mix is AlphaBeta with the `mix` heuristic, and Deepening:mix is Deepening with `mix` and 0.1 seconds per move. On the command line (`watch` and `tournament`) you can set their depth, heuristic and time.

### Heuristics

Minimax, AlphaBeta and Deepening look ahead, then judge the positions where they stop with a heuristic ([heuristics.md](docs/agents/heuristics.md)). Put its name after a colon, before or after the depth: `AlphaBeta:mix`, `AlphaBeta:8:mix`, `Minimax:4:mobility`, `Deepening:0.5s:mix`.

- `store` (the default): my store minus the opponent's, the seeds captured so far.
- `mix`: `store`, plus half a seed for each pit I can play more than the opponent, plus a tenth of a seed for each seed more in my row. The strongest: AlphaBeta with `mix` wins about 95% of the points against AlphaBeta with `store` at the same depth, and even `AlphaBeta:4:mix` beats plain `AlphaBeta` at depth 6.
- `seeds`, `weak`, `mobility`, `big`: `store` plus one board feature each (seeds in my row, pits with 1–2 seeds, pits I can play, pits with 12+ seeds), to test each feature alone.

## Tournament

Play many games between two AI agents, with no window, and compare them:

```sh
.venv/bin/awale tournament Random Random
```

Agent A is the first name and agent B the second. This plays 500 random openings of 6 moves, each twice with the agents swapping sides (1000 games), on all CPU cores. It takes about a second for Random.
It prints A's wins, draws and losses, A's points with a 95% confidence interval (a win is 1 point, a draw 1/2), the average difference in seeds, the time per move, and whether one agent is clearly stronger.

More games give a smaller interval. Four times more games make it two times smaller:

```sh
.venv/bin/awale tournament Random Random --openings 5000
```

The same `--seed` plays exactly the same games again:

```sh
.venv/bin/awale tournament Random Random --seed 1
```

Greedy against Random, and Greedy against itself:

```sh
.venv/bin/awale tournament Greedy Random
.venv/bin/awale tournament Greedy Greedy
```

Minimax against Greedy (about 10 seconds), and Minimax looking 4 moves ahead against Minimax looking 2 moves ahead (about 30 seconds):

```sh
.venv/bin/awale tournament Minimax Greedy
.venv/bin/awale tournament Minimax Minimax:2
```

AlphaBeta at depth 4 plays exactly the same games as Minimax at depth 4. With the same `--seed`, these two print the same wins, draws, losses and seeds; only the time per move differs:

```sh
.venv/bin/awale tournament Minimax Greedy --seed 1
.venv/bin/awale tournament AlphaBeta:4 Greedy --seed 1
```

AlphaBeta (6 moves ahead) against Minimax (4 moves ahead), about 1.5 minutes:

```sh
.venv/bin/awale tournament AlphaBeta Minimax
```

A tournament uses every CPU core, and a long one can make a laptop hot. `--workers 4` uses only 4 processes: it takes about twice as long, but the laptop stays cooler.

AlphaBeta with the `mix` heuristic against plain AlphaBeta, both 4 moves ahead (about half a minute):

```sh
.venv/bin/awale tournament AlphaBeta:4:mix AlphaBeta:4 --seed 1 --workers 4
```

Each board feature alone against plain AlphaBeta (see [heuristics.md](docs/agents/heuristics.md) for what they show):

```sh
.venv/bin/awale tournament AlphaBeta:4:seeds AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:weak AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:mobility AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:big AlphaBeta:4 --seed 1 --workers 4
```

AlphaBeta with `mix` against plain AlphaBeta at the default depth 6 (500 games, about 2 minutes):

```sh
.venv/bin/awale tournament AlphaBeta:mix AlphaBeta --openings 250 --seed 1 --workers 4
```

Deepening at a fixed depth plays exactly the same games as AlphaBeta at that depth, only faster. With the same `--seed`, these two print the same wins, draws, losses and seeds, and Deepening's time per move is about 2.6 times smaller (about 10 minutes each):

```sh
.venv/bin/awale tournament AlphaBeta:8:mix AlphaBeta:mix --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:8:mix AlphaBeta:mix --openings 250 --seed 1 --workers 4
```

Deepening with 0.1 seconds per move against AlphaBeta at depth 8, which thinks about as long (200 games, about 8 minutes). With a time limit the results change a little from run to run, even with the same `--seed`, because how deep Deepening gets depends on how busy the computer is:

```sh
.venv/bin/awale tournament Deepening:mix AlphaBeta:8:mix --openings 100 --seed 1 --workers 4
```

Save every game in a CSV file in `records/tournaments` (the last 10 tournaments are kept):

```sh
.venv/bin/awale tournament Random Random --save
```

All options:

```sh
.venv/bin/awale tournament --help
```

## Game records

The last 100 Play and Watch games are saved in `records/games`, one JSON file per game, named by the time the game ended.
Moves are written a-f for South's pits 1-6 and A-F for North's pits 1-6, so `c D` means South played its pit 3, then North its pit 4.

See the newest game:

```sh
ls records/games | tail -1
cat "records/games/$(ls records/games | tail -1)"
```

Replay a saved game in Python and look at any position in it:

```sh
.venv/bin/python
```

```python
from pathlib import Path
from awale.records import load_game

newest = sorted(Path("records/games").iterdir())[-1]
record = load_game(newest)
record.moves                     # ('c', 'D', 'a', ...)
game = record.replay()
game.positions[10]               # the position after 10 moves
```

A saved tournament CSV has one row per game, and its `record` column holds all the moves in the same letters.

## Run the tests

```sh
.venv/bin/pytest
```

This also plays 2000 random games in our engine and in OpenSpiel side by side, to check that our rules are right. It takes about 5 seconds.

Only the quick rule tests, without OpenSpiel:

```sh
.venv/bin/pytest tests/test_position.py tests/test_game.py
```

Only the agents' tests:

```sh
.venv/bin/pytest tests/test_agents.py tests/test_random_agent.py tests/test_greedy_agent.py tests/test_minimax_agent.py tests/test_alphabeta_agent.py tests/test_heuristics.py tests/test_deepening_agent.py
```

Only the Watch window tests:

```sh
.venv/bin/pytest tests/test_watch.py
```

Only the tournament and game record tests:

```sh
.venv/bin/pytest tests/test_tournament.py tests/test_records.py
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
