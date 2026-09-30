# Random

Code: `awale/agents/random_agent.py`. Tests: `tests/test_random_agent.py`.

## The idea

Random does not think at all. It looks at the legal moves and picks one, each with the same chance.

It is still useful. It is the baseline: any agent that cannot beat Random clearly is not really playing. It is also a quick opponent for testing the window and the tournament.

## How the code works

```python
class Agent(ABC):
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)


class RandomAgent(Agent):
    name = "Random"

    def choose_move(self, position: Position) -> int:
        return self.rng.choice(position.legal_moves())
```

- `Agent` is the interface every agent follows (`awale/agents/base.py`). The window, Watch and Tournament only call `choose_move`, so they work with any agent.
- `position.legal_moves()` already knows all the rules: empty pits are left out, and when the opponent's row is empty, only moves that feed them are left. So Random can never play an illegal move, and it does not need to know the rules itself.
- `self.rng` is the agent's own random generator. Every agent gets one from `Agent`, because later agents (MCTS) use chance too. We do not use the shared `random` module, for two reasons:
  - **Repeatable games.** `RandomAgent(seed=1)` always plays the same moves in the same positions. If a game shows a bug, we can play it again exactly. A tournament gives every agent its own seed, so `--seed` repeats a whole tournament.
  - **No hidden links.** With the shared module, one agent's choices would change the other agent's choices, and anything else that uses `random` would change both.
- `seed=None` (the default, used by the start menu) means a different game every time.

## An example

South to move, with North's pits written from North's own left:

```
South: 1 0 0 0 0 2     North: 1 2 4 4 4 4
```

South has two legal moves:

- pit 6: its 2 seeds land in North's pits 1 and 2, which become 2 and 3, so South captures 5 seeds;
- pit 1: its 1 seed moves to South's pit 2, and nothing happens.

Any person would play pit 6. Random plays it only half the time. This is exactly what the next agent, Greedy (step 6), fixes: it looks one move ahead and takes the move that captures the most.

When there is only one legal move, Random plays it, like everyone else. In the feeding position below, North's row is empty and only pit 6 can reach it:

```
South: 2 0 0 0 0 1     North: 0 0 0 0 0 0
```

## What the tests check

- It plays only legal moves, in 20 whole games.
- When there is one legal move, it plays that move.
- From the start position, 600 choices give every pit about 100 times (a fair choice).
- The same seeds give the same game, and other seeds give a different game.

## Random against Random

```sh
.venv/bin/awale tournament Random Random --openings 5000 --seed 1
```

```
A: Random    B: Random
10000 games: 5000 random openings of 6 moves, each played twice with the agents swapping sides.

A wins 4770 (47.7%), draws 564 (5.6%), loses 4666 (46.7%).
A's points: 50.5% ± 1.0%  (a win is 1 point, a draw 1/2; 95% confidence interval)
Seeds at the end, A minus B: +0.1 ± 0.3 on average.
Time per move: A 3 µs, B 3 µs.
By side: South won 4542, North won 4894, 564 draws.

The interval includes 50%, so these games cannot tell the two agents apart.
```

- **Even, as it should be.** A and B are the same agent, and A's points are 50.5% ± 1.0%. The interval includes 50%, so the small lead is just luck. This is the check that the tournament itself is fair.
- **North wins more often.** 4894 against 4542 is too big a gap to be luck (about 3.6 standard errors). After the 6 opening moves South is to move, so North is the second to move. Under random play, moving second seems to help a little. We saw the same in step 3 (North 977, South 891 from the start position). This is exactly why every opening is played twice with the agents swapping sides: each agent gets the good side as often as the bad one.
- **Fast.** 3 microseconds per move, and 10000 games take under 4 seconds on 8 cores.
- Draws are rare: under 6% of games end 24 to 24.

Before the tournament, in step 3, we ran a quick check of 2000 games from the start position with South always moving first: a game lasted 105 moves on average (from 24 to 332); 1516 games ended with a store reaching 25, 289 because a player could not feed the opponent, and 195 by repetition.
