# Random

Code: `awale/agents/random_agent.py`. Tests: `tests/test_random_agent.py`.

## The idea

Random does not think at all. It looks at the legal moves and picks one, each with the same chance.

It is still useful. It is the baseline: any agent that cannot beat Random clearly is not really playing. It is also a quick opponent for testing the window and the tournament, and later it plays the random openings of a tournament.

## How the code works

```python
class RandomAgent(Agent):
    name = "Random"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_move(self, position: Position) -> int:
        return self.rng.choice(position.legal_moves())
```

- `Agent` is the interface every agent follows (`awale/agents/base.py`). The window, Watch and Tournament only call `choose_move`, so they work with any agent.
- `position.legal_moves()` already knows all the rules: empty pits are left out, and when the opponent's row is empty, only moves that feed them are left. So Random can never play an illegal move, and it does not need to know the rules itself.
- `self.rng` is the agent's own random generator. We do not use the shared `random` module, for two reasons:
  - **Repeatable games.** `RandomAgent(seed=1)` always plays the same moves in the same positions. If a game shows a bug, we can play it again exactly.
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

A quick check before the real tournament (step 4): 2000 games, Random against Random, South always moving first.

- North won 977, South 891, and 132 were draws. That is close to even, and the tournament in step 4 will tell with a confidence interval whether North's small lead is real or just luck.
- A game lasts 105 moves on average (from 24 to 332).
- 1516 games ended with a store reaching 25, 289 because a player could not feed the opponent, and 195 by repetition.
