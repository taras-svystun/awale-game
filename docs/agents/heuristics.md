# Heuristics

Code: `awale/agents/heuristics.py`. Tests: `tests/test_heuristics.py`. Read [minimax.md](minimax.md) and [alphabeta.md](alphabeta.md) first: a heuristic is what they ask when their look-ahead stops.

This is not a new agent. It is a new part for the agents we have: Minimax and AlphaBeta can use any heuristic, and you pick one by name after a colon, like `AlphaBeta:mix` or `AlphaBeta:8:mix`.

## The idea

Minimax and AlphaBeta look a few moves ahead, then stop and ask a heuristic: "how good is this position for me?". Until now the only answer was `store_diff`: my store minus the opponent's. It only sees seeds that are already captured.

Most positions where the search stops are **quiet**: nobody captured anything in the last few moves. For `store_diff` they all look the same, so the search cannot tell a good quiet position from a bad one, and picks one of them at random. A better heuristic also looks at the **board**.

The plan (step 9) named four things to look at. Each one is a **feature**: a number counted on the board, always "mine minus the opponent's", so it is positive when the position is good for me.

| Feature | What it counts | Why it might matter |
|---|---|---|
| `row_seeds` | seeds in my row minus seeds in theirs | They are mine to sow, and they are mine when the game ends. |
| `weak_pits` | their pits with 1 or 2 seeds, minus mine | One more seed makes such a pit 2 or 3, so it can be captured. |
| `mobility` | my pits that are not empty, minus theirs | How many moves each player has to choose from. |
| `big_pits` | my pits with 12 or more seeds, minus theirs | Such a pit sows all the way around and on into the opponent's row again, and can capture a lot at once. |

A feature alone is not a heuristic. `weighted` adds features to `store_diff`, each one times a **weight**. The weight says how many captured seeds one unit of the feature is worth. With `mobility: 0.5`, one more pit I can play is worth half a captured seed.

We did not guess the weights. We let tournaments choose them.

## How the code works

```python
def mobility(position, me):
    return _count(position.pits(me), 1, 48) - _count(position.pits(me.opponent), 1, 48)

def row_seeds(position, me):
    return sum(position.pits(me)) - sum(position.pits(me.opponent))

def weighted(weights):
    def heuristic(position, me):
        value = store_diff(position, me)
        for feature, weight in weights.items():
            value += weight * feature(position, me)
        return round(value, 6)
    return heuristic

HEURISTICS = {
    "store": store_diff,
    "seeds": weighted({row_seeds: 0.1}),
    "weak": weighted({weak_pits: 0.5}),
    "mobility": weighted({mobility: 0.5}),
    "big": weighted({big_pits: 1}),
    "mix": weighted({mobility: 0.5, row_seeds: 0.1}),
}
```

Step by step.

**The features** are small functions with the same shape as a heuristic: they take a position and a player, and give a number. `_count(pits, low, high)` counts how many pits hold from `low` to `high` seeds: `_count(pits, 1, 48)` is the pits that are not empty, `_count(pits, 1, 2)` the weak ones.

**`weighted`** takes a dict `{feature: weight}` and builds a heuristic from it: a new function that starts from `store_diff` and adds each feature times its weight. A function that makes a function may look strange at first. It is the same as writing `def mix(position, me): return store_diff(...) + 0.5 * mobility(...) + 0.1 * row_seeds(...)` by hand, but each mix of weights is one line, and trying a new mix does not need a new function.

**`round(value, 6)`**: 0.1 has no exact value in binary, so `0.1 * 3` gives `0.30000000000000004`. Without rounding, two positions worth the same could score 0.3 and 0.30000000000000004, and Minimax would think one is better. Rounding makes them a real tie.

**`HEURISTICS`** gives each heuristic a name. `make_agent` reads the name after the colon: `AlphaBeta:mix`, `Minimax:4:seeds`, or `AlphaBeta:mix:8` (the order does not matter). Without a name, an agent uses `store`, so `AlphaBeta` still plays exactly like `Minimax` at the same depth, as in [alphabeta.md](alphabeta.md). There is one heuristic per feature, so each feature can be tried alone, and `mix`, the best we found.

**A won game stays the best.** The search scores a won game 100 or more (`WIN` in `minimax_agent.py`). A guess must never reach that, or the search could prefer a nice-looking position to a real win. `mix` is at most 48 + 0.5 × 6 + 0.1 × 48 = 55.8, and a test checks this for every heuristic in `HEURISTICS`.

## An example on a real position

South to move, stores 0 and 0, pits from each owner's own left:

```
South: 0 11 3 7 8 1     North: 0 8 0 4 4 2
```

At depth 2, nobody can capture anything in the next two moves, so `store_diff` scores every move 0. `mix` sees a clear difference:

```python
>>> make_agent("AlphaBeta:2", seed=0).think(position)
Thoughts(move=5, scores={2: 0, 3: 0, 4: 0, 5: 0, 6: 0}, line=(5, 1), positions=32, depth=2)
>>> make_agent("AlphaBeta:2:mix", seed=0).think(position)
Thoughts(move=3, scores={2: 0.0, 3: 2.6, 4: -0.3, 5: 0.0, 6: 1.0}, line=(3, 4), positions=32, depth=2)
```

North has two empty pits (1 and 3), so it has only 4 moves. Look at what South's moves do to that:

- **`b`** (11 seeds) and **`e`** (8 seeds) sow into every pit of North's row. North's empty pits get a seed each, and North has 6 moves again. North then plays `A` or `C` and is even: both rows have 5 pits to play and the same seeds. Worth **0**.
- **`c`** (3 seeds) drops them into South's own pits 4, 5 and 6. Nothing goes to North:

  ```
  after c    South: 0 11 0 8 9 2     North: 0 8 0 4 4 2
  ```

  Every North answer now sows seeds into South's row, and North's empty pits stay empty. North's best answer is `D`:

  ```
  after c D  South: 1 12 0 8 9 2     North: 0 8 0 0 5 3
  ```

  South has 5 pits to play and North 3: mobility +2. South has 32 seeds in its row, North 16: row seeds +16. So `mix` = 0 + 0.5 × 2 + 0.1 × 16 = **2.6**.
- **`f`** (1 seed) gives North's pit 1 one seed, which North plays at once: worth 1.0. **`d`** (7 seeds) feeds North too: −0.3.

So `mix` learned an idea that good Awalé players know: **do not feed the opponent**. Small moves keep my seeds at home. The opponent's empty pits stay empty, so it has fewer moves, and every move it makes sends seeds into my row. Sooner or later it runs out of good moves and has to give me something to capture.

At depth 6, `AlphaBeta` still scores all 5 moves 0, and `AlphaBeta:mix` prefers `f` (2.3) over `c` (1.8): looking further, it finds a better way to keep North short of moves.

## What the tournaments show

All tournaments use `--seed 1`, and run on 4 processes instead of all cores, which is kinder to a laptop.

**Each feature alone**, against plain `store_diff`, at depth 4 (1000 games each, about half a minute):

```sh
.venv/bin/awale tournament AlphaBeta:4:seeds AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:weak AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:mobility AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:big AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:mix AlphaBeta:4 --seed 1 --workers 4
```

| A (at depth 4) | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|
| `seeds` | 862, 28, 110 | 87.6% ± 2.0% | +13.7 | 1.1 ms and 0.8 ms |
| `weak` | 382, 89, 529 | 42.6% ± 2.9% | −1.8 | 1.3 ms and 0.9 ms |
| `mobility` | 959, 14, 27 | 96.6% ± 1.1% | +15.2 | 1.6 ms and 1.0 ms |
| `big` | 513, 70, 417 | 54.8% ± 3.0% | +2.4 | 1.1 ms and 0.8 ms |
| `mix` | 946, 15, 39 | 95.3% ± 1.2% | +17.2 | 1.6 ms and 0.9 ms |

A heuristic that looks at the board costs time: `mix` takes almost twice as long per move as `store_diff`, because it is called on thousands of positions per move. It is still very quick at depth 4.

We first tried each feature with several weights, using a small script that is not in the repo. These are A's points against `AlphaBeta:4`, 1000 games each, same seed:

| Weight | 0.1 | 0.25 | 0.5 | 1 | −0.5 |
|---|---|---|---|---|---|
| `row_seeds` | **87.6%** | 81.2% | 68.3% | 37.3% | |
| `weak_pits` | | 50.2% | 42.6% | 19.4% | 84.2% |
| `mobility` | | 95.2% | **96.6%** | 91.5% | 30.5% |
| `big_pits` | | | | 54.8% (and 49.9% at 3) | |

What we learned:

- **Mobility is by far the most useful feature.** Worth half a captured seed per pit, it wins 96.6% of the points against `store_diff`. With a minus sign (fewer moves are better) it loses badly.
- **Seeds in my row help, but only with a small weight.** At 0.1 they win 87.6%. At 1, a seed at home is worth as much as a captured one, and the agent hoards seeds instead of capturing: it loses.
- **Weak pits were a surprise.** We expected "my pits with 1–2 seeds are a danger" to help. It does the opposite: the bigger the weight, the worse it plays, and with a minus sign it wins 84%. We think this is because the search already sees every real capture within its depth, so it does not need a guess about danger. What a pit with 1–2 seeds really gives is a cheap move that keeps the other seeds at home: it is mobility in disguise. A heuristic should judge what the search cannot see, and tournaments are how we find out what that is.
- **Big pits change nothing.** A pit with 12+ seeds is rare, and when one is about to be played, the search sees its captures anyway.

**Features together.** Then we added features on top of the best one, `mobility`, and played against it:

| A (at depth 4) | A's points against `mobility` |
|---|---|
| mobility 0.5 + row seeds 0.1 | **67.2% ± 2.8%** |
| mobility 0.5 + row seeds 0.05 | 64.2% ± 2.9% |
| mobility 0.5 + row seeds 0.2 | 59.4% ± 3.0% |
| mobility 0.5 + big pits 1 | 60.6% ± 2.9% |
| mobility 0.5 + weak pits 0.25 | 51.7% ± 3.0% |
| mobility 0.5 + weak pits −0.25 | 46.7% ± 3.0% |
| mobility 0.35 | 48.2% ± 3.0% |
| mobility 0.7 | 55.7% ± 3.0% |

And against mobility 0.5 + row seeds 0.1, nothing we added was better: big pits 1 (48.4%) or 2 (45.1%), mobility 0.7 (50.0%), mobility 0.7 + big pits 1 (50.7%). So `mix` is **mobility 0.5 + row seeds 0.1**. You can check the step from `mobility` to `mix`:

```sh
.venv/bin/awale tournament AlphaBeta:4:mix AlphaBeta:4:mobility --seed 1 --workers 4
```

`mix` wins 642, draws 59 and loses 299 of these 1000 games: 67.2% ± 2.8% of the points, 6.9 seeds ahead on average.

Notice that against `store_diff`, `mix` (95.3%) does not score more than `mobility` (96.6%), but against each other `mix` wins clearly. Against a weak opponent both are near 100%, and there is not much room left to tell them apart. To compare two strong agents, play them against each other.

**At AlphaBeta's own depth.** The weights were chosen at depth 4, where tournaments are quick. Do they still help at depth 6, and is a better heuristic worth more than looking further?

```sh
.venv/bin/awale tournament AlphaBeta:mix AlphaBeta --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:4:mix AlphaBeta --openings 250 --seed 1 --workers 4
.venv/bin/awale tournament AlphaBeta:mix AlphaBeta:8 --openings 100 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `AlphaBeta:mix` (depth 6) | `AlphaBeta` (depth 6) | 500 | 470, 15, 15 | 95.5% ± 1.7% | +15.6 | 11.9 ms and 6.0 ms |
| `AlphaBeta:4:mix` | `AlphaBeta` (depth 6) | 500 | 400, 22, 78 | 82.2% ± 3.2% | +9.2 | 1.5 ms and 5.4 ms |
| `AlphaBeta:mix` (depth 6) | `AlphaBeta:8` | 200 | 158, 12, 30 | 82.0% ± 5.1% | +9.4 | 10.5 ms and 33.9 ms |

- **The weights chosen at depth 4 work just as well at depth 6**: 95.5% of the points against plain AlphaBeta, the same as at depth 4.
- **A better heuristic is worth more than looking two moves further.** `AlphaBeta:4:mix` beats `AlphaBeta` at depth 6 with 82% of the points, while thinking 3.6 times less per move. And `AlphaBeta:mix` at depth 6 beats `AlphaBeta:8` just as clearly, at a third of its time. In step 8, two more moves of depth won about 81%. Here a better guess at the end of the look-ahead wins the same, for less time instead of more.
- The heuristic is not free: at the same depth `mix` takes about twice as long per move as `store_diff`. That is a good trade, since looking 2 moves deeper costs 3–5 times more.

`AlphaBeta:mix` is now the agent to beat. Step 10 makes it faster with move ordering and gives it a time limit instead of a fixed depth: see [deepening.md](deepening.md).

## In Watch

```sh
.venv/bin/awale watch AlphaBeta:mix AlphaBeta
```

Pause and step through a quiet part of the game. `AlphaBeta` often scores several moves the same, because nothing can be captured within its sight. `AlphaBeta:mix` gives them different scores, with decimals, and you can see from the board why: its move usually keeps its seeds at home and leaves North's empty pits empty.

In the start menu, `AlphaBeta:mix` is the last button, so you can also play against it.

## What the tests check

- Each feature counts the right thing on a hand-made position, and is exactly as bad for one player as it is good for the other.
- `weighted` adds each feature times its weight to `store_diff`.
- No heuristic in `HEURISTICS` can reach the value of a won game.
- The example above: at depth 2, `store_diff` scores every move 0, and `mix` scores `c` 2.6 and plays it.
- `AlphaBeta:2:mix` clearly beats `AlphaBeta:2` in a small tournament.
- `make_agent` reads a heuristic's name after the colon, with or without a depth, in any order.
