# Minimax

Code: `awale/agents/minimax_agent.py` and `awale/agents/heuristics.py`. Tests: `tests/test_minimax_agent.py`.

## The idea

Greedy looks at its own move and stops. Minimax also looks at the opponent's answer, at our answer to that, and so on, a fixed number of moves deep. The **depth** is how many moves it looks ahead, counting both players' moves: depth 4 is our move, their answer, our move, their answer.

The question is: which answer do we expect from the opponent? Minimax expects the **best one for them**, which is the worst one for us. So:

- on **our** turns we take the move with the **highest** value for us (max);
- on **their** turns we expect the move with the **lowest** value for us (min).

That is where the name comes from: max, min, max, min, down the tree of moves.

When the look-ahead stops, the game is usually not over. Minimax still needs a number for that position, so it asks a **heuristic**. Our first heuristic is `store_diff`: my store minus the opponent's store, the seeds I am ahead right now.

```
                 now (South to move)                   max: South takes its best
          /          |           \
       pit 1       pit 2   ...   pit 6                 min: North answers with its best
      /  |  \     /  |  \       /  |  \
     ...         ...            ...                    max, min, ... until the depth runs out
                                                       then store_diff judges each position
```

The value of a move is not what it captures, but what we still have after the best play of both sides, as far as we can see. That fixes Greedy's weakness: a move that takes 2 seeds and gives away 5 is worth −3, not +2.

## How the code works

```python
class MinimaxAgent(Agent):
    name = "Minimax"

    def __init__(self, seed=None, depth=DEPTH, heuristic=store_diff):
        ...

    def think(self, position: Position) -> Thoughts:
        me = position.to_move
        self.positions = 0
        results = {pit: self.minimax(position.play(pit), self.depth - 1, me) for pit in position.legal_moves()}
        self.positions += len(results)
        scores = {pit: value for pit, (value, _) in results.items()}
        best = max(scores.values())
        move = self.rng.choice([pit for pit, score in scores.items() if score == best])
        line = (move, *results[move][1])
        return Thoughts(move, scores, line, self.positions, self.depth)

    def minimax(self, position, depth, me):
        if position.ends_game():
            return self.final_value(position, me, depth), ()
        if depth == 0:
            return self.heuristic(position, me), ()
        results = []
        for pit in position.legal_moves():
            value, line = self.minimax(position.play(pit), depth - 1, me)
            results.append((value, (pit, *line)))
        self.positions += len(results)
        best = max if position.to_move is me else min
        return best(results, key=lambda result: result[0])
```

Step by step.

**`think`**, the top of the tree:

1. `me = position.to_move`: who we are. All values in the search are "how good for `me`", on every level.
2. For each legal move we play it and ask `minimax` how good the new position is, with one move less of depth left (`self.depth - 1`), because we just used one.
3. `scores` keeps the value of each of our moves. These are the numbers drawn over the pits in Watch.
4. As in Greedy, if several moves have the same best value we pick one at random. From the start position every move scores 0 at depth 4, so without this Minimax would always open with pit 1.
5. `line` is the chosen move followed by the line of play `minimax` found after it: what Minimax expects both players to do next.

**`minimax`**, one position somewhere in the tree. It is **recursive**: it calls itself for each position one move deeper. It returns two things: the value, and the line of play that leads to it.

1. If the game is over in this position, we do not need to guess: `final_value` says win, loss or draw. `Position.ends_game()` is the same check `Game` uses: a store has 25 seeds, or the player to move has no legal move. (A repetition also ends a game, but a `Position` does not remember earlier positions, so the search does not see repetitions.)
2. If the depth has run out, we stop and guess: `self.heuristic(position, me)`, which is `store_diff`.
3. Otherwise we try every legal move and ask `minimax` about each new position, with one move less of depth. Each answer comes back with its line, and we put our move in front of it: `(pit, *line)`.
4. `best = max if position.to_move is me else min`: this is the whole idea in one line. If it is our turn here, we will choose our best move. If it is the opponent's turn, we expect them to choose our worst.
5. `self.positions` counts every position we reached, for the "work done" in Watch.

**`final_value`**, a position where the game has ended:

```python
final = position.with_rows_collected()
difference = final.store(me) - final.store(me.opponent)
if difference > 0:
    return WIN + depth
if difference < 0:
    return -WIN - depth
return 0
```

- First the seeds left on the board go to each row's owner, exactly as `Game` does when a game ends. Without this, a game that ends 24–24 would look like "4 seeds ahead" if our store had 24 and theirs 20, with 4 seeds still in their row.
- A win is worth `WIN = 100`. `store_diff` can never be more than 48, so any win beats any number of seeds, and any loss is worse than any number of seeds. A draw is 0.
- `+ depth`: `depth` is how much look-ahead is still left. A win found after 1 move has more left than a win found after 3 moves, so it scores higher, and Minimax takes the quick win. For a loss it is the other way round: a slow loss scores higher than a quick one, so Minimax makes the opponent work for it. That is why you may see scores like `+103` or `−102` in Watch.

**`store_diff`** (in `heuristics.py`):

```python
def store_diff(position: Position, me: Side) -> int:
    return position.store(me) - position.store(me.opponent)
```

It is a separate function, not part of Minimax, because a heuristic and a search are two different things. In step 9 we write better heuristics and give them to the same search: `MinimaxAgent(heuristic=...)`.

**Depth in the name.** `Minimax` looks 4 moves ahead. On the command line, `Minimax:6` looks 6 ahead and `Minimax:2` only 2. `make_agent` in `awale/agents/__init__.py` reads the name, and the name with its depth goes into game records.

**How much work.** Each extra move of depth multiplies the work by about the number of legal moves, often 5 or 6. From the start position:

| Depth | Positions | Time |
|---|---|---|
| 2 | 42 | 0.3 ms |
| 4 | 1 246 | 7 ms |
| 6 | 33 797 | 0.19 s |
| 7 | 172 954 | 0.95 s |

Depth 8 would take about 5 seconds per move. Alpha-beta (step 8) gives the same moves while skipping most of these positions.

## An example on a real position

The position from [greedy.md](greedy.md): South to move, stores 0 and 0, pits from each owner's own left.

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

Greedy saw pit 2 and pit 6 as equal (both capture 2) and picked one at random. Minimax at depth 2:

```python
>>> MinimaxAgent(seed=0, depth=2).think(Position.setup(south=(5, 5, 5, 5, 0, 1), north=(1, 7, 7, 0, 6, 6)))
Thoughts(move=6, scores={1: -5, 2: -3, 3: -5, 4: -5, 6: 2}, line=(6, 2), positions=28, depth=2)
```

- **Pit 2**: South captures 2, then North's best answer is its pit 6, which captures 5 from South's pits 5 and 6. 2 − 5 = **−3**.
- **Pit 6**: South captures 2 and leaves pits 5 and 6 empty, so no North move captures anything. 2 − 0 = **+2**.
- **Pits 1, 3, 4**: they capture nothing and leave South's pits 5 and 6 holding 1 or 2 seeds, so North captures 5: **−5**.

Minimax plays pit 6 every time, whatever its seed. It sees what Greedy could not.

Now the same position at depth 4, as Watch shows it:

```python
>>> MinimaxAgent(seed=0, depth=4).think(...)
Thoughts(move=6, scores={1: -5, 2: -3, 3: -4, 4: -7, 6: -2}, line=(6, 2, 1, 5), positions=697, depth=4)
```

Pit 6 is still the best, but now it is worth −2. The expected line is `f B a E`:

```
f  South pit 6, captures 2   South: 5 5 5 5 0 0   North: 0 7 7 0 6 6   stores 2-0
B  North pit 2               South: 6 6 6 5 0 0   North: 0 0 8 1 7 7   stores 2-0
a  South pit 1               South: 0 7 7 6 1 1   North: 1 0 8 1 7 7   stores 2-0
E  North pit 5, captures 4   South: 1 8 8 7 0 0   North: 1 0 8 1 0 8   stores 2-4
```

After North's `B`, every South move leaves something for North to take. Minimax found the one that loses least: `a` gives away 4, the others give more. So depth 4 tells a different story than depth 2: pit 6 wins 2 seeds now, but North gets them back two moves later.

Is that the truth? Not quite. The line stops right after North's capture, and South never gets its answer. This is called the **horizon effect**: the search stops at a fixed depth, and whatever happens one move later is invisible. The value of the same move changes with the depth:

| Depth | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Value of pit 6 | +2 | +2 | +2 | −2 | +2 | 0 |

With an odd depth the last move is ours, so the search ends on our capture and looks a little too hopeful. With an even depth the last move is the opponent's, and it looks a little too gloomy. This is why stronger programs keep searching past the depth while captures are still possible, and why depth alone is not the whole story.

## In Watch

```sh
.venv/bin/awale watch Minimax Greedy
```

- **Move scores**: over each pit, the value of that move after looking 4 moves ahead, in seeds ahead (or `±100` and more for a win or a loss it can see). Its choice is in yellow.
- **Expected line**: four moves in letters, like `f B a E`. The first is its move, the second the answer it expects. It is the line both players would play if both thought exactly like Minimax at this depth. The real opponent may play something else.
- **Work done**: about 1 000 positions and a few milliseconds per move at depth 4.

Try `Minimax:6` against `Minimax:2` to see what two more moves of look-ahead are worth.

## What the tests check

- At depth 1 it scores moves exactly like Greedy: with both stores at 0, "seeds ahead after one move" is just the capture.
- At depth 2 it sees the capture it gives away, on the position above, with the exact scores.
- It scores for North as well as for South.
- It takes a win and scores it above any seed count, with the depth still left added: `WIN + 3` at depth 4 for a win in one move.
- It avoids a move that lets the opponent reach 25, where Greedy sees all moves as equal.
- When the game ends, the seeds left on the board go to each row's owner before the result is judged.
- The expected line is `depth` moves long, starts with its move, and every move in it is legal.
- It counts positions: 6 + 36 = 42 at depth 2 from the start.
- Ties are broken at random; depth below 1 is an error.
- It plays only legal moves in whole games, and the same seeds give the same game.
- `Minimax:2` beats Greedy clearly in a small tournament.

## Tournaments

All tournaments below use `--seed 1`, so you can play exactly the same games again.

**Against Greedy and Random.**

```sh
.venv/bin/awale tournament Minimax:2 Greedy --openings 5000 --seed 1
.venv/bin/awale tournament Minimax Greedy --openings 2000 --seed 1
.venv/bin/awale tournament Minimax Random --openings 1000 --seed 1
```

| A | B | Games | A's points | Seeds, A minus B | Time per move, A |
|---|---|---|---|---|---|
| Minimax:2 | Greedy | 10 000 | 99.2% ± 0.2% | +23.0 | 0.2 ms |
| Minimax | Greedy | 4 000 | 99.5% ± 0.2% | +21.1 | 4.2 ms |
| Minimax | Random | 2 000 | 100.0% (1999 wins, 1 draw) | +28.9 | 5.3 ms |

- **Looking at the answer is almost everything.** Depth 2 is just "my capture minus the best capture it gives away", and that alone wins 99% of the points against Greedy. Greedy's weakness from [greedy.md](greedy.md) is not a rare trap: it gives away seeds in almost every game.
- **Depth 4 does not do much better against Greedy**, because there is almost nothing left to win: 99.2% becomes 99.5%. To see what depth is worth, Minimax must play against itself.

**Against itself, at other depths.**

```sh
.venv/bin/awale tournament Minimax Minimax:2 --openings 2000 --seed 1
.venv/bin/awale tournament Minimax Minimax:3 --openings 2000 --seed 1
.venv/bin/awale tournament Minimax:5 Minimax --openings 250 --seed 1
.venv/bin/awale tournament Minimax:6 Minimax --openings 250 --seed 1
.venv/bin/awale tournament Minimax Minimax --openings 2000 --seed 1
```

| A | B | Games | A's points | Seeds, A minus B | Time per move, A |
|---|---|---|---|---|---|
| Minimax (depth 4) | Minimax:2 | 4 000 | 77.6% ± 1.2% | +10.2 | 2.9 ms |
| Minimax (depth 4) | Minimax:3 | 4 000 | 75.9% ± 1.3% | +8.2 | 2.6 ms |
| Minimax:5 | Minimax (depth 4) | 500 | 76.3% ± 3.6% | +9.3 | 12 ms |
| Minimax:6 | Minimax (depth 4) | 500 | 83.5% ± 3.1% | +10.5 | 63 ms |
| Minimax | Minimax | 4 000 | 50.9% ± 1.5% | +0.1 | 2.8 ms |

- **Every extra move of depth wins clearly.** One move more (5 against 4, or 4 against 3) gives about 76% of the points, two moves more (4 against 2, 6 against 4) about 78–84%. Seeing further is worth a lot, and we are far from the depth where it stops helping.
- **It costs a lot too.** Each move of depth multiplies the time by about 4–5. Depth 6 wins 83.5% against depth 4, but thinks 20 times longer. This is what alpha-beta (step 8) is for: the same moves as Minimax, much faster, so we can afford more depth.
- **Minimax against itself is even**, 50.9% ± 1.5%, so the tournament is fair to it. There are more draws than with Greedy (9% against 5%): two careful players leave fewer seeds for each other.
- The times per move in a tournament are lower than from the start position, because later in a game there are fewer seeds and fewer legal moves.

Minimax at depth 4 is now the agent to beat. Alpha-beta (step 8) must choose the same moves, only faster.
