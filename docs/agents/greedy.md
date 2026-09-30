# Greedy

Code: `awale/agents/greedy_agent.py`. Tests: `tests/test_greedy_agent.py`.

## The idea

Greedy looks one move ahead. It tries each legal move, counts the seeds that move would capture, and plays the move that captures the most. If several moves capture the same number, it picks one of them at random.

It never thinks about what the opponent does next. That is its whole strength and its whole weakness:

- **Strength:** it never misses a capture. Random misses them all the time, so Greedy beats Random in more than 9 games out of 10.
- **Weakness:** it does not see the capture it gives away. It will happily take 2 seeds and leave 5 for the opponent.

Greedy is the first agent that *searches*, even if only one move deep. Minimax (step 7) is the same idea, but it also looks at the opponent's answer, and at our answer to that, and so on.

## How the code works

```python
class GreedyAgent(Agent):
    name = "Greedy"

    def think(self, position: Position) -> Thoughts:
        me = position.to_move
        scores = {pit: position.play(pit).store(me) - position.store(me) for pit in position.legal_moves()}
        best = max(scores.values())
        move = self.rng.choice([pit for pit, score in scores.items() if score == best])
        return Thoughts(move, scores, line=(move,), positions=len(scores), depth=1)
```

Step by step:

1. `me = position.to_move`: remember who we are, South or North. After a move it is the other player's turn, so we must remember it before playing.
2. `position.play(pit)` gives the position after that move. `Position` never changes, so trying a move does not touch the real game. We only look.
3. `.store(me) - position.store(me)` is how many seeds our store grew: the seeds this move captures. The engine applies all the rules for us: capture chains, the 12+ seeds skip, and the grand slam (which captures nothing, so it scores 0).
4. `scores` is a dict like `{1: 0, 2: 2, 6: 2}`: pit → seeds captured.
5. `best` is the biggest capture, and we keep every pit that reaches it.
6. `self.rng.choice(...)` picks one of those pits at random. Why not just `max(scores, key=scores.get)`? Because `max` returns the first best pit, the leftmost one. In most positions no move captures anything, so every score is 0, and Greedy would always play its leftmost pit. That is a bias with no reason behind it. At random, Greedy plays like Random whenever it has nothing to capture. `self.rng` is the agent's own seeded generator (see [random.md](random.md)), so the same seed still gives the same game.
7. Greedy writes `think`, not `choose_move`, because it has thoughts to show:
   - `scores`: the capture for each legal move, drawn over the pits in Watch;
   - `line=(move,)`: it looks only one move ahead, so the line it expects is just its own move;
   - `positions=len(scores)`: it looked at one position after each legal move;
   - `depth=1`: one move ahead.

   `Agent.choose_move` is built from `think`, so the tournament, which calls `choose_move`, works without extra code.

## An example on a real position

This position came up in a game of Greedy against Greedy, after 4 moves. South to move, stores 0 and 0, pits from each owner's own left:

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

Greedy's thoughts:

```python
>>> GreedyAgent(seed=0).think(Position.setup(south=(5, 5, 5, 5, 0, 1), north=(1, 7, 7, 0, 6, 6)))
Thoughts(move=6, scores={1: 0, 2: 2, 3: 0, 4: 0, 6: 2}, line=(6,), positions=5, depth=1)
```

Two moves capture 2 seeds:

- **Pit 2**: its 5 seeds go into South's pits 3, 4, 5, 6 and North's pit 1, which becomes 2. South captures 2.
- **Pit 6**: its 1 seed goes into North's pit 1, which becomes 2. South captures 2.

To Greedy they are the same, so it picks one at random (over 1000 seeds: pit 2 503 times, pit 6 497 times). But they are not the same at all. Look at the board after each one, with North's own Greedy scores:

```
After pit 2:  South: 5 0 6 6 1 2   North: 0 7 7 0 6 6    North's captures: {2: 0, 3: 0, 5: 2, 6: 5}
After pit 6:  South: 5 5 5 5 0 0   North: 0 7 7 0 6 6    North's captures: {2: 0, 3: 0, 5: 0, 6: 0}
```

After pit 2, South's pits 5 and 6 hold 1 and 2 seeds. North plays its pit 6: 6 seeds, one in each South pit, so pits 5 and 6 become 2 and 3, and North captures 5. South won 2 and lost 5.

After pit 6, South's pits 5 and 6 are empty. North's seeds make them 1, never 2 or 3, and no North move captures anything.

A person sees this with one more move of thinking. Greedy cannot, because it never looks at the opponent's answer. With seed 0 it happens to play pit 6; with seed 37, in the game this position came from, it played pit 2. Minimax at depth 2 would score pit 2 as 2 − 5 = −3 and pit 6 as 2 − 0 = +2, and play pit 6 every time.

## In Watch

```sh
.venv/bin/awale watch Greedy Random
```

Over each pit Greedy may play you see how many seeds that move captures, and its choice in yellow. Most of the time every score is 0: in Greedy-against-Greedy games, 69% of moves had nothing to capture, and then Greedy plays like Random. The expected line is just its own move, and the work done is one position per legal move, depth 1, about 30 microseconds.

## What the tests check

- It takes a capture over a quiet move, and the bigger of two captures, with the right scores.
- It counts captures for North as well as for South.
- A grand slam scores 0, because it captures nothing.
- From the start position (nothing to capture), 600 seeds give every pit about 100 times: ties are broken at random.
- Its thoughts: the line is its own move, depth 1, one position per legal move.
- It plays only legal moves in whole games, and the same seeds give the same game.
- It beats Random clearly in a small tournament of 100 games.

## Tournaments

Greedy against Random:

```sh
.venv/bin/awale tournament Greedy Random --openings 5000 --seed 1
```

```
A: Greedy    B: Random
10000 games: 5000 random openings of 6 moves, each played twice with the agents swapping sides.

A wins 9194 (91.9%), draws 174 (1.7%), loses 632 (6.3%).
A's points: 92.8% ± 0.5%  (a win is 1 point, a draw 1/2; 95% confidence interval)
Seeds at the end, A minus B: +20.4 ± 0.3 on average.
Time per move: A 30 µs, B 3 µs.
By side: South won 4888, North won 4938, 174 draws.

A (Greedy) is stronger: its whole interval is above 50%.
```

- **Much stronger.** 92.8% ± 0.5% of the points. Only taking the captures that are there is enough to beat Random almost every game.
- **By a lot of seeds.** Greedy ends with 20 more seeds than Random on average, something like 34 to 14.
- **It still loses 6% of games.** Greedy gives away captures all the time, as the example above shows, and now and then Random happens to take enough of them.
- **Still fast.** 30 µs per move: 10 times slower than Random, because it plays every legal move once, but 10000 games still take about 2 seconds on 8 cores.

Greedy against Greedy, to check that the tournament is fair to it too:

```sh
.venv/bin/awale tournament Greedy Greedy --openings 5000 --seed 1
```

```
(part of the output)
A wins 4776 (47.8%), draws 497 (5.0%), loses 4727 (47.3%).
A's points: 50.2% ± 1.0%  (a win is 1 point, a draw 1/2; 95% confidence interval)
By side: South won 4737, North won 4766, 497 draws.
```

Even, as it should be. North's small advantage we saw with Random against Random (4894 to 4542) is gone here (4766 to 4737 is within luck).

Greedy is now the agent to beat. Minimax (step 7) must win clearly against Greedy, not only against Random.
