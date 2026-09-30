# Deepening

Code: `awale/agents/deepening_agent.py`. Tests: `tests/test_deepening_agent.py`. Read [alphabeta.md](alphabeta.md) first: Deepening is AlphaBeta with three things added.

## The idea

AlphaBeta has two weak spots.

1. **It tries moves from left to right.** [alphabeta.md](alphabeta.md) showed that alpha-beta skips more when the best move is tried first. After South's `c`, it tried North's `A` first and cut a lot. Had it tried `F` first, it would have cut even more. Left to right is just luck.
2. **It has a fixed depth.** At depth 8 it may answer in 5 ms in one position and take 2 seconds in another. We cannot say "think for half a second", which is what a person playing against it wants, and what is fair in a tournament.

Deepening fixes both with three ideas that work together.

### 1. Move ordering: try the most promising moves first

Which move is most promising, before we search it? Two cheap guesses:

- **The move that captures most**: Greedy's idea. A capture often is the best move, and when it is not, the opponent's capture back often is.
- **The move that was best here last time.** If we already searched this position a little less deep, its best move then is very likely its best move now.

The second guess needs an earlier search of the same position. That is the next idea.

### 2. Iterative deepening: 1 move ahead, then 2, then 3, ...

Instead of one search 8 moves deep, Deepening searches 1 move deep, then 2, then 3, and so on up to 8. This looks wasteful: why search 7 moves deep, then throw it away and search 8 deep?

Because each depth costs about **2 times** more than the one before (for AlphaBeta with a good order; Minimax is 4–5 times). So all the shallower searches together cost about as much as the last one alone. And they pay for themselves: each search remembers the best move in every position it saw (`best_moves`), and the next search tries that move first. So the deep search gets a good order almost everywhere.

### 3. A narrow window at the top

AlphaBeta searches every one of our moves with the widest window, so each one gets its exact score ([alphabeta.md](alphabeta.md) explains why). Deepening does not need that. It tries the best move of the last search first, and it is usually still the best. For every other move, it only needs to prove "this is worse", not "this is exactly −7". So the window for the other moves starts **just below the best score so far**. A move that is worse fails quickly and gets only an **upper bound**: "−7 or less". In Watch that score is shown as `≤-7`.

Why "just below" and not "at" the best score? When several moves are equally good, Minimax and AlphaBeta choose one of them at random. To do the same, Deepening must know every move that **ties** for the best. With the window starting at the best score, a tie would only get "this or less". Starting a hair lower (`TIE`, 0.0000001) gives every tie its exact score. This works because our scores never differ by less than 0.000001: every heuristic rounds to 6 decimals, and a won game is a whole number.

So at a fixed depth, Deepening **chooses exactly the moves AlphaBeta chooses**, from the same random seed, only faster. Its scores are the same for the best moves, and only upper bounds for the others.

### And the time limit

Now a time limit is easy. Deepening searches deeper and deeper, and when the time is up it stops in the middle of a search, throws that unfinished search away, and plays the best move of the **deepest search it finished**. It always finishes the search 1 move deep, so it always has a move.

It also stops early when looking deeper cannot change anything:

- **More than half of the time is gone.** The next depth takes about as long as all the ones before it together, so it would not finish anyway.
- **Every line of play ended the game** before the depth ran out. A deeper search sees exactly the same.
- **The best move surely wins, or every move surely loses.** A deeper search finds the same win (a quicker one would have been found already), or the same loss.

## How the code works

`DeepeningAgent` is a subclass of `AlphaBetaAgent`. It keeps `final_value` and the heuristic, and replaces `think` and `alphabeta`. It has two new methods: `search` for our moves at the top, and `ordered_moves`.

### `ordered_moves`: the order

```python
def ordered_moves(self, position):
    mover = position.to_move
    children = [(pit, position.play(pit)) for pit in position.legal_moves()]
    self.positions += len(children)
    children.sort(key=lambda child: child[1].store(mover), reverse=True)
    best = self.best_moves.get(position)
    if best is not None:
        children.sort(key=lambda child: child[0] != best)
    return children
```

1. Play every legal move, to see the position it leads to. AlphaBeta plays a move only when it gets to it, so a move that is cut is never played. Here we play them all first, because we need the positions to sort them. `positions` counts all of them, so "Work done" is honest.
2. Sort by the mover's store after the move: the biggest capture first. Python's `sort` is **stable**: moves that capture the same stay in pit order, even with `reverse=True`.
3. If an earlier search found a best move in this position, sort again, with the key `pit != best`. That is `False` for the best move and `True` for the others, and `False` comes first. The sort is stable again, so the other moves keep their capture order.

### `alphabeta`: the same search, with three extra lines

```python
def alphabeta(self, position, depth, me, alpha, beta):
    if time.perf_counter() > self.deadline:
        raise OutOfTime
    if position.ends_game():
        return self.final_value(position, me, depth), ()
    if depth == 0:
        self.reached_horizon = True
        return self.heuristic(position, me), ()
    ...                                         # the same loop as AlphaBeta's,
    for pit, child in self.ordered_moves(position):   # but over ordered_moves
        ...
    self.best_moves[position] = best_line[0]
    return best, best_line
```

- **The clock.** The search may be 12 moves deep in the tree when the time runs out. `raise OutOfTime` leaves all of it at once: the exception goes up through every `alphabeta` call until `think` catches it. That is simpler than returning a special "no time" value from every call.
- **`reached_horizon`** notes that at least one line stopped because the depth ran out, not because the game ended. `think` uses it to know that a deeper search could change something.
- **`best_moves[position]`** remembers the best move here, for the next, deeper search. The key is the whole `Position`, which works because a `Position` never changes and can be a dict key. The same position can be reached by different move orders, and it shares one entry.

### `search`: our moves at the top

```python
def search(self, position, depth, me):
    scores, upper_bounds, lines = {}, set(), {}
    alpha = -INFINITY
    for pit, child in self.ordered_moves(position):
        low = alpha - TIE
        value, line = self.alphabeta(child, depth - 1, me, low, INFINITY)
        scores[pit], lines[pit] = value, (pit, *line)
        if value <= low:
            upper_bounds.add(pit)
        if value > alpha:
            alpha = value
            self.best_moves[position] = pit
    return scores, upper_bounds, lines
```

Each of our moves is searched with the window from `low` (a hair below the best score so far) to +infinity. By the promise of alpha-beta ([alphabeta.md](alphabeta.md)), a value above `low` is exact, and a value of `low` or less means only "this or less": an upper bound. The first move gets the window from −infinity, so its score is always exact.

### `think`: deeper and deeper

```python
def think(self, position):
    me = position.to_move
    started = time.perf_counter()
    self.positions, self.best_moves = 0, {}
    done = None
    depth = 0
    while self.depth is None or depth < self.depth:
        depth += 1
        if depth > 1 and self.time_limit is not None:
            self.deadline = started + self.time_limit
        self.reached_horizon = False
        try:
            scores, upper_bounds, lines = self.search(position, depth, me)
        except OutOfTime:
            break
        finally:
            self.deadline = math.inf
        done = depth, scores, upper_bounds, lines
        if not self.reached_horizon or abs(max(scores.values())) >= WIN:
            break
        if self.time_limit is not None and time.perf_counter() - started > self.time_limit / 2:
            break
    depth, scores, upper_bounds, lines = done
    best = max(scores.values())
    move = self.rng.choice(sorted(pit for pit, score in scores.items() if score == best))
    return Thoughts(move, dict(sorted(scores.items())), lines[move], self.positions, depth, frozenset(upper_bounds))
```

- `best_moves` starts empty for each move we think about, and is filled by each depth for the next one.
- The deadline is only set from depth 2 on, so the search 1 move deep always finishes and `done` is never `None`.
- `finally` runs whether the search finished or ran out of time, so the deadline is never left set for the next call.
- The three reasons to stop early are the ones from [the idea](#and-the-time-limit).
- The random choice is made once, at the end, from the moves in pit order, the same way as AlphaBeta. That is why the same seed gives the same moves.

### Its name: depth, time, heuristic

`make_agent` reads the options after the colons in any order: a whole number is the depth, a number with an `s` is the time in seconds, and a name is a heuristic.

| Name | Depth | Time limit |
|---|---|---|
| `Deepening` | none | 0.1 s |
| `Deepening:0.5s` | none | 0.5 s |
| `Deepening:8` | 8 | none |
| `Deepening:12:1s` | 12 | 1 s |
| `Deepening:1s:mix` | none | 1 s, with the `mix` heuristic |

With a depth and no time, it always searches exactly that deep, and plays exactly like AlphaBeta at that depth. Only the time limit makes it "think for 0.1 s". The default heuristic is `store`, like every search agent; the start menu has `Deepening:mix`.

## An example on a real position

The position from [greedy.md](greedy.md), [minimax.md](minimax.md) and [alphabeta.md](alphabeta.md): South to move, stores 0 and 0.

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

Here is `Deepening:8` searching deeper and deeper:

| Depth | Order at the top | Best | Scores (≤ is an upper bound) | Positions at this depth | AlphaBeta at this depth |
|---|---|---|---|---|---|
| 1 | b f a c d | f | a ≤0, b 2, c ≤0, d ≤0, f 2 | 5 | 5 |
| 2 | b f a c d | f | a ≤−5, b −3, c ≤−5, d ≤−5, f 2 | 28 | 28 |
| 3 | **f** b a c d | f | a ≤−5, b ≤−3, c ≤−2, d ≤−2, f 2 | 63 | 93 |
| 4 | f b a c d | f | a ≤−5, b ≤−3, c ≤−4, d ≤−7, f −2 | 165 | 311 |
| 5 | f b a c d | f | a ≤−4, b ≤−1, c ≤−4, d ≤−5, f 2 | 418 | 963 |
| 6 | f b a c d | f | a ≤−7, b ≤−3, c ≤−4, d ≤−7, f 0 | 929 | 2 715 |
| 7 | f b a c d | f | a ≤−3, b ≤0, c ≤0, d ≤−3, f 2 | 1 740 | 8 537 |
| 8 | f b a c d | f | a ≤−3, b ≤−1, c ≤−2, d ≤−7, f 0 | 3 659 | 17 883 |

Follow it down:

- **Depth 1.** The order is by captures: `b` and `f` both capture 2, so they come first, in pit order. `b` scores 2 and becomes the best. `f` ties it, so it gets its exact score 2 too (thanks to `TIE`). The others only prove "0 or less". Both `b` and `f` score 2, and `best_moves` remembers `b`, the first one found.
- **Depth 2.** `b` is tried first, and now scores −3: after `b`, North captures 5. `f` scores 2 and becomes the best.
- **Depth 3 and on.** `f` is tried first. Its exact score sets the window, and every other move only has to be proved worse. From here on, each depth costs about 2 times the one before, and AlphaBeta's cost grows faster.
- **Upper bounds.** At depth 6, `d` shows `≤−7`. Its exact score, from AlphaBeta, is −9. Deepening never learns that, because "−7 or less" already proves that `d` is worse than `f`'s 0.

At depth 8, Deepening looked at 5 + 28 + 63 + 165 + 418 + 929 + 1 740 + 3 659 = **7 007** positions in all 8 searches together. AlphaBeta at depth 8 looked at **17 883**, 2.5 times more, for the same move.

## How much work it saves

On 30 positions from random games (the ones `tests/test_alphabeta_agent.py` uses), the total over all 30:

| Heuristic | Depth | AlphaBeta, positions | AlphaBeta, time | Deepening, positions | Deepening, time | Deepening is faster by |
|---|---|---|---|---|---|---|
| store | 4 | 9 568 | 0.05 s | 12 299 | 0.06 s | 0.9 times |
| store | 6 | 75 202 | 0.42 s | 72 937 | 0.36 s | 1.2 times |
| store | 8 | 512 741 | 2.85 s | 321 001 | 1.58 s | 1.8 times |
| store | 10 | 3 200 886 | 17.9 s | 1 290 800 | 6.4 s | 2.8 times |
| mix | 4 | 9 446 | 0.07 s | 10 353 | 0.06 s | 1.2 times |
| mix | 6 | 79 272 | 0.59 s | 58 210 | 0.33 s | 1.8 times |
| mix | 8 | 579 073 | 4.29 s | 259 566 | 1.45 s | 3.0 times |
| mix | 10 | 3 874 602 | 28.5 s | 1 076 293 | 6.0 s | 4.8 times |

Deepening's positions include all its shallower searches, and every move it played only to sort it.

- **The deeper, the bigger the saving.** At depth 4 there is not much to save, and the extra searches at depths 1–3 cost as much as they save. At depth 10 with `mix`, Deepening is almost 5 times faster.
- **It saves more with `mix` than with `store`.** With `store`, many moves tie (nothing can be captured in sight), and every tie must get its exact score, so the narrow window helps less. With `mix`, ties are rare.
- In the same time, this is about **2 moves deeper** at depths 8–10, since each move of depth costs AlphaBeta 2.5–3 times more.

You can check the time on your own computer:

```sh
.venv/bin/python -m timeit -s "from awale.agents import make_agent; from awale.engine import Position" "make_agent('AlphaBeta:8:mix', seed=0).think(Position.start())"
.venv/bin/python -m timeit -s "from awale.agents import make_agent; from awale.engine import Position" "make_agent('Deepening:8:mix', seed=0).think(Position.start())"
```

## In Watch

```sh
.venv/bin/awale watch Deepening:mix AlphaBeta:mix
```

Pause and step. Deepening's move has an exact score, and most other moves show `≤`: it only proved them worse. "Work done" shows how deep it got in its 0.1 seconds. The depth changes from move to move: usually 8 to 10 moves deep, and deeper near the end of the game, when each player has only a few moves to choose from.

```sh
.venv/bin/awale watch Deepening:1s:mix Deepening:mix
```

With 1 second per move it looks about 3 moves deeper than with 0.1 seconds.

## What the tests check

- At depths 1 to 5 on 30 positions, with `store` and with `mix`, it chooses exactly AlphaBeta's move from the same seed. Its exact scores are AlphaBeta's scores, and each upper bound is at least the true score and below the best move's score.
- The same where a game ends inside the look-ahead: the same move, and a win found at a shallower depth is the same win.
- Whole games and a small tournament are the same as AlphaBeta's.
- At depth 7 with `mix`, it looks at fewer positions than AlphaBeta, counting all its shallower searches.
- The example above: at depth 6 it plays `f`, the other moves are upper bounds, and `d`'s `≤−7` is really −9.
- The order: the last best move first, then the biggest captures, then pit order.
- The promise of the window: a value inside is exact, one outside is only a bound.
- With a time limit it stops in time, more time looks deeper, and even with almost no time it looks 1 move ahead.
- It stops early when every line ends the game and when it surely wins.
- The names: `Deepening` thinks for 0.1 s, `Deepening:8` has no time limit, `Deepening:mix:12:2s` sets all three, and bad times are refused.

## Tournaments

All tournaments use `--seed 1` and `--workers 4`, which is kinder to a laptop than all cores.

**At a fixed depth: the same games, faster.** With a depth and no time limit, Deepening chooses exactly AlphaBeta's moves, so with the same seed it plays exactly the same games:

```sh
.venv/bin/awale tournament AlphaBeta:6:mix AlphaBeta:4:mix --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:6:mix AlphaBeta:4:mix --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:8:mix AlphaBeta:mix --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:8:mix AlphaBeta:mix --openings 250 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A |
|---|---|---|---|---|---|---|
| `AlphaBeta:6:mix` | `AlphaBeta:4:mix` | 500 | 351, 32, 117 | 73.4% ± 3.7% | +9.8 | 9.7 ms |
| `Deepening:6:mix` | `AlphaBeta:4:mix` | 500 | 351, 32, 117 | 73.4% ± 3.7% | +9.8 | 5.9 ms |
| `AlphaBeta:8:mix` | `AlphaBeta:mix` | 500 | 331, 29, 140 | 69.1% ± 3.9% | +7.6 | 59.5 ms |
| `Deepening:8:mix` | `AlphaBeta:mix` | 500 | 331, 29, 140 | 69.1% ± 3.9% | +7.6 | 23.0 ms |

The same wins, draws and losses to the game, in 1.6 times less time at depth 6 and 2.6 times less at depth 8. This is the promise of move ordering, kept on 1000 real games.

**With a time limit: how strong is it?** A tournament with a time limit is **not exactly repeatable**, even with the same `--seed`: how deep Deepening gets depends on how busy the computer is, so the numbers change a little each time. Games with 0.1 s per move are also slow, so these use fewer openings.

```sh
.venv/bin/awale tournament Deepening:mix AlphaBeta:mix --openings 100 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:mix AlphaBeta:8:mix --openings 100 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:mix Deepening:mix --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament Deepening:0.4s:mix Deepening:mix --openings 50 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `Deepening:mix` (0.1 s) | `AlphaBeta:mix` (depth 6) | 200 | 153, 10, 37 | 79.0% ± 5.4% | +9.2 | 63 ms and 9.7 ms |
| `Deepening:mix` (0.1 s) | `AlphaBeta:8:mix` | 200 | 123, 11, 66 | 64.2% ± 6.5% | +4.2 | 64 ms and 57 ms |
| `Deepening:mix` | `Deepening:mix` | 100 | 52, 5, 43 | 54.5% ± 9.6% | +1.3 | 63 ms and 63 ms |
| `Deepening:0.4s:mix` | `Deepening:mix` (0.1 s) | 100 | 82, 2, 16 | 83.0% ± 7.3% | +9.2 | 239 ms and 63 ms |

- **In the same time, Deepening beats AlphaBeta.** Against `AlphaBeta:8:mix`, which thinks about as long per move (57 ms against 64 ms), it gets 64% of the points. It sees about 2 moves further in the same time, and the time limit lets it spend more on hard positions and less on easy ones.
- **It thinks less than its limit.** With 0.1 s it uses 63 ms per move on average: it does not start a depth that would not finish, and it stops early when the game is decided.
- **Against itself it is even**: 54.5% ± 9.6%, and the interval includes 50%.
- **More time still wins.** With 4 times more time, it wins 83% of the points: about 2 moves deeper, the same gain as in [alphabeta.md](alphabeta.md) and [minimax.md](minimax.md). Awalé is far from solved at these depths.

`Deepening:mix` is now the agent to beat, and it is the one in the start menu. The next step is MCTS, a very different kind of search.
