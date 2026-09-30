# AlphaBeta

Code: `awale/agents/alphabeta_agent.py`. Tests: `tests/test_alphabeta_agent.py`. Read [minimax.md](minimax.md) first: AlphaBeta is Minimax with one trick added.

## The idea

Minimax tries every line of play to the end of its depth, and most of that work is wasted. Think of choosing a move like this:

> I tried my move **a**, and whatever the opponent answers, I end up at least even: **a** is worth 0.
> Now I try my move **b**. The opponent's first answer to **b** leaves me 3 seeds behind.

Do I need to look at the opponent's other answers to **b**? No. **b** is already worth −3 or less, because the opponent picks the answer that is worst for me. Maybe another answer is even worse, but I do not care how bad **b** is: I have **a**, and **a** is better. So I stop looking at **b** and go on to **c**.

That is the whole idea of alpha-beta: **as soon as a move is proved worse than one we already have, stop looking at it**. It is called **pruning**: we cut whole branches off the tree of moves. The result is exactly the same as Minimax's, because we only skip lines that could never be played if both sides play their best.

The same reasoning works on every level of the tree, for both players. Each position in the search gets two numbers:

- **alpha**: what **we** can already get somewhere earlier in the tree. If this position turns out worth alpha or less to us, we will not let the game come here: we play the other way.
- **beta**: what the **opponent** can already hold us to somewhere earlier. If this position turns out worth beta or more to us, the opponent will not let the game come here.

The two numbers are a **window**. Only a value inside the window can change a choice above us. So:

- on **our** turn, as soon as one of our moves is worth **beta or more**, we stop: the opponent will avoid this position anyway, so our other moves do not matter;
- on **their** turn, as soon as one of their answers is worth **alpha or less** to us, we stop: we will avoid this position anyway, so their other answers do not matter.

When we stop early, the value we return is not exact, only "beta or more" (or "alpha or less"). That is enough: the position above only needs to know that it will not go this way.

## How the code works

```python
class AlphaBetaAgent(MinimaxAgent):
    name = "AlphaBeta"

    def __init__(self, seed=None, depth=DEPTH, heuristic=store_diff):   # DEPTH = 6
        super().__init__(seed, depth, heuristic)

    def minimax(self, position, depth, me):
        return self.alphabeta(position, depth, me, -INFINITY, INFINITY)

    def alphabeta(self, position, depth, me, alpha, beta):
        if position.ends_game():
            return self.final_value(position, me, depth), ()
        if depth == 0:
            return self.heuristic(position, me), ()
        our_turn = position.to_move is me
        best, best_line = (-INFINITY if our_turn else INFINITY), ()
        for pit in position.legal_moves():
            self.positions += 1
            value, line = self.alphabeta(position.play(pit), depth - 1, me, alpha, beta)
            if our_turn:
                if value > best:
                    best, best_line = value, (pit, *line)
                alpha = max(alpha, best)
            else:
                if value < best:
                    best, best_line = value, (pit, *line)
                beta = min(beta, best)
            if alpha >= beta:
                break
        return best, best_line
```

Step by step.

**What it takes from Minimax.** `AlphaBetaAgent` is a subclass of `MinimaxAgent`, so it inherits `think`, `final_value` and the heuristic unchanged. `think` calls `self.minimax(...)` for each of our moves. AlphaBeta replaces only that method: its `minimax` calls `alphabeta` with the widest window, from −infinity to +infinity. We come back to why below.

**`alphabeta`**, one position somewhere in the tree. It starts like `minimax`:

1. A position where the game ends gets its real value from `final_value`: a win, a loss or a draw.
2. When the depth runs out, the heuristic (`store_diff`) guesses.

Then it tries the legal moves one by one, and after each one:

3. It keeps the best value so far: the highest on our turn, the lowest on theirs. `best` starts at −infinity on our turn (any move beats it) and at +infinity on theirs. It only replaces `best` with a **strictly** better value, so on a tie it keeps the leftmost pit, like Minimax's `max` and `min` do. That keeps the expected line the same as Minimax's.
4. It moves its side of the window. On our turn, `alpha` goes up to our best so far: "we can already get this much". On their turn, `beta` goes down to their best so far: "they can already hold us to this much".
5. `if alpha >= beta: break`. This is the pruning. On our turn it means: our best move here is already worth beta or more, and the opponent can hold us to beta somewhere earlier. The opponent will not let the game come here, so our other moves do not matter. On their turn it is the same the other way round.

The window goes **down** the tree: each position gives its children the window it has at that moment, narrowed by the moves it already tried. So a cut deep in the tree can be caused by a move tried much higher up.

`self.positions` counts only the positions we really looked at, so "Work done" in Watch shows how much alpha-beta saved.

**Why the widest window at the top.** A textbook alpha-beta also narrows the window at the top: once our first move is worth 0, it looks at our other moves with alpha = 0. We do not, for two reasons:

- Watch draws a score over every pit. With a narrow window, a worse move would only get "0 or less", not its real score.
- When several moves share the best value, Minimax picks one of them at random. To pick the same one, AlphaBeta must know exactly which moves tie for the best, and a narrow window cannot tell "equal to 0" from "0 or less".

So every one of our moves gets its exact score, and AlphaBeta's thoughts are exactly Minimax's thoughts: the same move, the same scores, the same expected line. Only the number of positions is different. Below the top, the window narrows as usual. This costs something: a narrow window at the top would look at about a third fewer positions at depth 6. We may come back to it in step 10.

**Depth.** Minimax looks 4 moves ahead by default. AlphaBeta looks 6 ahead by default (`DEPTH = 6`), because it can afford to: about 15 ms per move. `AlphaBeta:4` looks 4 ahead, like Minimax, and `AlphaBeta:8` looks 8 ahead.

**How much work it saves.** From the start position:

| Depth | Minimax, positions | Minimax, time | AlphaBeta, positions | AlphaBeta, time |
|---|---|---|---|---|
| 2 | 42 | 0.3 ms | 42 | 0.2 ms |
| 4 | 1 246 | 7 ms | 555 | 3 ms |
| 6 | 33 797 | 0.19 s | 4 852 | 28 ms |
| 7 | 172 954 | 0.95 s | 9 663 | 56 ms |
| 8 | 884 368 | 5.5 s | 29 021 | 0.17 s |
| 10 | too slow to wait for | | 163 300 | 0.96 s |

The deeper it looks, the more it saves: nothing at depth 2, 2 times fewer positions at depth 4, 7 times at depth 6, 18 times at depth 7, 30 times at depth 8. AlphaBeta at depth 8 is quicker than Minimax at depth 7. There is nothing to skip at depth 2, because every one of our moves gets its exact score, and that needs all of the opponent's answers. The first cuts happen at depth 3.

How much alpha-beta saves depends on the **order** in which it tries the moves. If the best move is tried first, everything after it is cut quickly. If it is tried last, nothing is cut. We try the pits from left to right, which is not a clever order. Move ordering (step 10) tries the most promising moves first, and then alpha-beta can look about twice as deep as Minimax in the same time.

## An example on a real position

The position from [greedy.md](greedy.md) and [minimax.md](minimax.md): South to move, stores 0 and 0, pits from each owner's own left.

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

Minimax and AlphaBeta at depth 3 think exactly the same:

```python
>>> MinimaxAgent(seed=0, depth=3).think(position)
Thoughts(move=6, scores={1: -5, 2: -3, 3: -2, 4: -2, 6: 2}, line=(6, 2, 1), positions=145, depth=3)
>>> AlphaBetaAgent(seed=0, depth=3).think(position)
Thoughts(move=6, scores={1: -5, 2: -3, 3: -2, 4: -2, 6: 2}, line=(6, 2, 1), positions=93, depth=3)
```

The same move, scores and line, from 93 positions instead of 145. Let us follow one branch: South plays its pit 3 (`c`).

```
after c    South: 5 5 0 6 1 2     North: 2 8 7 0 6 6     stores 0-0, North to move
```

Now North has 5 answers, and for each one South has 1 more move before the depth runs out. The window starts wide open: alpha = −infinity, beta = +infinity.

1. **North `A`** (pit 1). None of South's 5 replies captures anything, so `A` is worth **0** to South. Now beta = 0: North knows it can hold South to 0.
2. **North `B`** (pit 2). South's first reply, `a`, sows its last seed into North's pit 1 and captures 3. So `B` is worth **+3 or more** to South, whatever South's other replies give. North will never play `B`: `A` is better for North. So we **skip South's other 5 replies** (`b` to `f`). Minimax looks at all 6.
3. **North `C`** (pit 3). The same: South's `a` captures 3, `C` is worth +3 or more, skip 5 replies.
4. **North `E`** (pit 5). North captures 2, but South's `a` captures 3 back: +1 or more, still better than `A`'s 0 for South. Skip 4 replies.
5. **North `F`** (pit 6). North captures 5 from South's pits 5 and 6. South's best reply `a` captures 3 back: −5 + 3 = **−2**. Worse for South than 0, so this is North's new best, and beta = −2. We have to look at all 4 of South's replies here, because none of them reaches beta.

So `c` is worth −2, with the expected line `c F a`, exactly as Minimax says. AlphaBeta looked at 5 + 5 + 1 + 1 + 1 + 4 = **17** positions, Minimax at 5 + 5 + 6 + 6 + 5 + 4 = **31**.

Notice when the cuts happened: after `A` gave North a good answer early. If North's pits had been tried in the order `F`, `A`, `B`, ..., beta would be −2 from the start, and even `A` would be cut after its first reply. That is why the order of moves matters.

## In Watch

```sh
.venv/bin/awale watch AlphaBeta:4 Minimax
```

Both look 4 moves ahead. Pause, and step through a few moves: the move scores and the expected line are the same kind of numbers as Minimax's, and at the same depth they are exactly the same. In "Work done", AlphaBeta looks at 2–3 times fewer positions.

```sh
.venv/bin/awale watch AlphaBeta Minimax
```

AlphaBeta at its default depth 6 against Minimax at depth 4: it thinks a few times longer than Minimax, and sees two moves further.

## What the tests check

- At depths 1 to 5, on 30 positions from random games, its thoughts are exactly Minimax's: the same move, the same score for every move, the same expected line. Only the number of positions differs.
- The same holds where a game ends inside the look-ahead: a win, a loss it must avoid, the seeds left going to each row, and a position with North to move.
- It looks at the same 42 positions as Minimax at depth 2 from the start, less than half of Minimax's at depth 4, and less than a fifth at depth 6.
- The example above: after South's `c`, the value is −2 with the line `F a`, from exactly 17 positions.
- The promise in the docstring: a value inside the window is exact, and a value outside is only a bound, never past the true value.
- Whole games with the same seeds are move for move the same as Minimax's, and a small tournament gives the same results.
- It looks 6 moves ahead by default, and `AlphaBeta:8` sets the depth.

## Tournaments

All tournaments below use `--seed 1`, so you can play exactly the same games again.

**The same games as Minimax, only faster.** At the same depth, with the same `--seed`, AlphaBeta plays exactly the games Minimax plays, so the tournament prints exactly the same results. Only the time per move differs.

```sh
.venv/bin/awale tournament Minimax Greedy --openings 1000 --seed 1
.venv/bin/awale tournament AlphaBeta:4 Greedy --openings 1000 --seed 1
.venv/bin/awale tournament Minimax:6 Greedy --openings 250 --seed 1
.venv/bin/awale tournament AlphaBeta:6 Greedy --openings 250 --seed 1
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A |
|---|---|---|---|---|---|---|
| Minimax (depth 4) | Greedy | 2 000 | 1973, 9, 18 | 98.9% ± 0.4% | +20.9 | 4.1 ms |
| AlphaBeta:4 | Greedy | 2 000 | 1973, 9, 18 | 98.9% ± 0.4% | +20.9 | 1.9 ms |
| Minimax:6 | Greedy | 500 | 497, 2, 1 | 99.6% ± 0.5% | +22.2 | 95 ms |
| AlphaBeta:6 | Greedy | 500 | 497, 2, 1 | 99.6% ± 0.5% | +22.2 | 14 ms |

This is the promise of step 8 kept on thousands of real games: the same moves, 2 times faster at depth 4 and almost 7 times faster at depth 6.

**What the saved time buys.** Faster is only useful if we spend the time on looking deeper.

```sh
.venv/bin/awale tournament AlphaBeta Minimax --openings 1000 --seed 1
.venv/bin/awale tournament AlphaBeta:8 Minimax:6 --openings 250 --seed 1
.venv/bin/awale tournament AlphaBeta:8 AlphaBeta --openings 250 --seed 1
.venv/bin/awale tournament AlphaBeta AlphaBeta --openings 1000 --seed 1
```

| A | B | Games | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|
| AlphaBeta (depth 6) | Minimax (depth 4) | 2 000 | 81.9% ± 1.6% | +10.6 | 10 ms and 2.9 ms |
| AlphaBeta:8 | Minimax:6 | 500 | 81.0% ± 3.3% | +9.4 | 72 ms and 66 ms |
| AlphaBeta:8 | AlphaBeta (depth 6) | 500 | 81.0% ± 3.3% | +9.4 | 70 ms and 10 ms |
| AlphaBeta | AlphaBeta | 2 000 | 50.2% ± 2.1% | −0.1 | 10 ms and 10 ms |

- **In the same time, AlphaBeta looks two moves deeper, and that wins about 81% of the points.** `AlphaBeta:8` and `Minimax:6` think about as long per move (72 ms and 66 ms), and AlphaBeta wins clearly. Nothing is smarter about its moves: it just sees further for the same work.
- **AlphaBeta at depth 6 against Minimax at depth 4** gets 81.9%, close to the 83.5% that `Minimax:6` got against Minimax in [minimax.md](minimax.md), as it should: they are the same player. The small difference is chance, the games are not the same ones.
- **`AlphaBeta:8` against `AlphaBeta` gives exactly the same result as against `Minimax:6`**: 391 wins, 28 draws, 81 losses, in both. That is no accident: AlphaBeta at depth 6 plays the same moves as Minimax at depth 6, and `--seed 1` gives the same openings, so all 500 games are the same. Only B's time per move changed, from 66 ms to 10 ms.
- **AlphaBeta against itself is even**, 50.2% ± 2.1%, so the tournament is fair to it. About 10% of these games are draws.
- These tournaments take longer than the time per move suggests, because games between two careful players last much longer: about 125 moves for AlphaBeta against Minimax and 150 for AlphaBeta against itself, but only about 40 against Greedy, which loses its seeds quickly.

AlphaBeta at depth 6 is now the agent to beat, and step 9 will give it better heuristics than `store_diff`.
