# OpenSpiel's agents

Code: `awale/agents/openspiel_agents.py`. Tests: `tests/test_openspiel_agents.py`.

[OpenSpiel](https://github.com/google-deepmind/open_spiel) is a library of games and game AI from DeepMind. It has its own Awalé, the game `oware`, with exactly our rules: our tests play 2000 random games in both and check that they agree after every move (see [ADR 0001](../adr/0001-own-python-engine-openspiel-as-reference.md)). It also has search algorithms that work for any game, among them MCTS and alpha-beta.

These two agents hand our game to OpenSpiel and play the move OpenSpiel chooses:

- **OpenSpielMCTS**: OpenSpiel's MCTS, written in C++.
- **OpenSpielAlphaBeta**: OpenSpiel's alpha-beta, written in Python, with our heuristics.

It helps to know [mcts.md](mcts.md) and [alphabeta.md](alphabeta.md) first: these are the same ideas.

## The idea

### Why play against code we did not write

Every agent so far was written by us, and tested against agents written by us. If we got something subtly wrong in all of them, our tournaments would never show it. OpenSpiel's agents are **outside opponents**: written by other people, used and tested by many. They answer two questions:

1. **Is our code right?** OpenSpiel's alpha-beta with our heuristic must give every move the same score as our AlphaBeta, and the two must be even in a tournament. If not, one of them has a bug.
2. **How much is speed worth?** OpenSpiel's MCTS does what our MCTS does, but in C++: about 7 times more playouts per second. Our MCTS lost to `AlphaBeta:4` with 0.1 s per move and beat it with 1 s (see [mcts.md](mcts.md)). Does a fast MCTS catch up with `Deepening:mix`?

### OpenSpiel only starts from the start

OpenSpiel keeps the game in its own form, a **state**. From Python, a state can only be made at the start of a game and then moved forward with moves. There is no way to say "here is a board, think about it".

So an OpenSpiel agent cannot think about a lone position, like our agents do. It needs **the whole game**: every move from the start. It plays them all again in OpenSpiel, which takes a few microseconds per move, and then OpenSpiel's search starts from the state it reached.

That is why agents now have a second method, `think_in_game(game)`. Tournament, Play and Watch call it. For our agents it just calls `think(game.position)`; OpenSpiel's agents write their own. [ADR 0002](../adr/0002-openspiel-agents-replay-the-game.md) explains the choice.

One good side effect: OpenSpiel's state knows the earlier positions, so OpenSpiel's search sees when a [repetition](../../CONTEXT.md) would end the game. Ours does not.

## How the code works

### From our game to OpenSpiel's state

```python
OWARE = pyspiel.load_game("oware")

def openspiel_state(game):
    start = game.positions[0]
    if start != Position.start(start.to_move):
        raise ValueError("OpenSpiel's agents can only play a game that begins at the start position")
    state = OWARE.new_initial_state()
    for pit in game.moves:
        state.apply_action(pit - 1)
    return state
```

- **A move means the same in both.** OpenSpiel's action `k` is the mover's pit `k + 1`, counted from their own left, like ours. So `pit - 1` works for South and North alike.
- **OpenSpiel's player 0 always moves first.** When South moved first, player 0 is South. When North moved first, player 0 is North. Since moves are counted from the mover's own left, replaying the moves needs no change either way.
- A game set up by hand (`Game(start=...)` with another position) cannot be replayed. Only the tests make such games, and the agent refuses them.

For the other direction, `position_of(state)` reads OpenSpiel's board back into our `Position`, with player 0 as South. Our tests check that after replaying a game, `position_of` gives exactly our position (or the board turned around, when North moved first). OpenSpiel's alpha-beta needs it to call our heuristics.

### Both agents share one parent

```python
class OpenSpielAgent(Agent):
    def think(self, position):
        return self.think_in_game(Game(start=position))

    def think_in_game(self, game):
        return self.search(openspiel_state(game))
```

`think` with only a position makes a game with no moves. That works for the start position, and raises the error above for any other.

### OpenSpielMCTS

```python
def search(self, state):
    seed = self.rng.getrandbits(31)
    bot = pyspiel.MCTSBot(
        OWARE,
        pyspiel.RandomRolloutEvaluator(1, seed),
        UCT_C,                                  # 2.0
        self.playouts or NO_PLAYOUT_LIMIT,
        MEMORY_MB,
        True,                                   # solve
        seed,
        False,                                  # verbose
        pyspiel.ChildSelectionPolicy.UCT,
        self.time_limit or -1,                  # -1: no time limit
    )
    root = bot.mcts_search(state)
    best = root.best_child()
    ...
```

`MCTSBot` is OpenSpiel's MCTS in C++. We set it up the way OpenSpiel's own examples do:

- **`RandomRolloutEvaluator(1, seed)`**: judge a new node with 1 random playout, like ours.
- **`UCT_C = 2`**: the C in the UCB formula. OpenSpiel counts a loss as −1 and a win as +1, a range twice as wide as our 0 to 1. Its shares of wins are twice as far apart as ours, so its C must be twice as big to explore as much. C = 2 for OpenSpiel is C = 1 for our MCTS: a little less exploring than our √2 ≈ 1.41. In [mcts.md](mcts.md), C = 1 and C = √2 played about even.
- **`solve = True`**: the **MCTS-Solver**, one of the ideas at the end of [mcts.md](mcts.md). When the tree reaches the end of the game below a node, the node is marked as surely won or lost, and its result is exact from then on. Its parent then knows that a move leads to a sure win and plays it, without waiting for playouts to agree.
- **The seed** comes from our agent's own random generator, a new one for each move. So the same seed and a number of playouts always give the same game, like our MCTS.

`mcts_search` returns the top of OpenSpiel's tree. Its nodes look like ours (see [mcts.md](mcts.md)), with OpenSpiel's names:

| OpenSpiel's node | Our `Node` |
|---|---|
| `action` | `move - 1` |
| `explore_count` | `visits` |
| `total_reward`, from −1 to +1 per playout | `wins`, from 0 to 1 per playout |
| `outcome`: the exact result, once the solver proved it | – |
| `children` | `children` |

**The move** is `root.best_child()`: OpenSpiel's choice. A move the solver proved won comes first, then the move tried most, like ours.

**The scores** are turned into our share of wins, from 0 to 1, so Watch shows them like our MCTS's:

```python
def win_share(node):
    if node.outcome:
        return (node.outcome[node.player] + 1) / 2
    return (node.total_reward / node.explore_count + 1) / 2
```

An average of −1 (lost every playout) becomes 0.00, an average of +1 becomes 1.00. `node.player` is the player who moved into the node, the one the score is for.

**Two differences from our MCTS** you can see in Watch:

- OpenSpiel's first playout starts at the top, before any move is in the tree. With 1 playout (or almost no time), it knows nothing about the moves, and the agent plays a random one with no scores.
- OpenSpiel adds a child for every legal move at once, but tries them one by one. A move with no playout yet gets no score. Ours tries every move at least once.

**Work done**: the playouts (the top's `explore_count`), the depth of the tree, and its positions. Our MCTS's positions also count every move played in its playouts; OpenSpiel does not tell us those, so its count is much smaller.

### OpenSpielAlphaBeta

OpenSpiel's `alpha_beta_search(game, state, value_function, maximum_depth, maximizing_player_id)` is textbook alpha-beta, written in Python. It is general: it knows nothing about Awalé. Where it stops looking, it calls `value_function(state)`, and it wants values from −1 (a loss) to +1 (a win). So we give it our heuristic, divided by `WIN` (100), which no heuristic reaches:

```python
def search(self, state):
    me = state.current_player()

    def value(state):
        self.positions += 1
        return self.heuristic(position_of(state), Side(me)) / WIN

    scores, answers = {}, {}
    for action in state.legal_actions():
        score, answer = minimax.alpha_beta_search(
            OWARE, state.child(action), value, self.depth - 1, maximizing_player_id=me
        )
        scores[action + 1] = round(score * WIN, 6)
        answers[action + 1] = answer
    move = max(scores, key=scores.get)
    ...
```

- **A score for every move.** `alpha_beta_search` returns only the best move and its value. To show a score over every pit, like our AlphaBeta, we call it once for the position after each move, one move less deep. This is what our AlphaBeta does at the top too: every move gets its exact score.
- **Back to seeds.** The score is multiplied by `WIN` again, so Watch shows `-7` like our agents, not `-0.07`. A won game is worth exactly `WIN`: OpenSpiel's alpha-beta does not prefer a quick win to a slow one, as ours does with `WIN + depth`.
- **The move** is the first one with the best score. `max` returns the first of equal values, and OpenSpiel's alpha-beta also keeps the first best move. Ours chooses at random between equal moves.
- **`me` does not change.** `value` judges every position for the player to move at the top, whoever is to move there, as `maximizing_player_id` asks.
- **`position_of`**, with player 0 as South, is fine for the heuristic even when North moved first: a heuristic looks at "my" pits and "the opponent's", never at which of them is South.
- **The expected line** is only 2 moves: the move and OpenSpiel's answer. `alpha_beta_search` does not return more.
- **Work done** counts only the positions where it called the heuristic: OpenSpiel's alpha-beta does not count the others.

## An example on a real position

OpenSpiel needs a real game, so the position from [greedy.md](greedy.md) will not do (nobody reached it by playing). This one comes after 10 moves from the start, `e E a F b A e E d A`. South to move, stores 0 and 4:

```
South: 0 0 8 0 1 9     North: 0 9 8 6 1 2
```

South can play `c`, `e` or `f`. Greedy plays `c`, which captures 2 now.

**Alpha-beta.** The two alpha-betas give exactly the same scores, at depth 4 and at depth 6:

| Agent | c | e | f | Move |
|---|---|---|---|---|
| `AlphaBeta:4` | −7 | **−6** | −8 | e |
| `OpenSpielAlphaBeta:4` | −7 | **−6** | −8 | e |
| `AlphaBeta:6` | −10 | **−7** | −9 | e |
| `OpenSpielAlphaBeta:6` | −10 | **−7** | −9 | e |

All three moves lose seeds; `e` loses the fewest. Greedy's `c` captures 2 but gives North more back. Ours looked at 2213 positions at depth 6, and OpenSpiel's called the heuristic 1541 times, at the end of its look-ahead.

**MCTS**, with the same seed (0) and a fixed number of playouts:

| Agent | c | e | f | Move | Depth of the tree |
|---|---|---|---|---|---|
| `MCTS:1000` | **0.41** | 0.40 | 0.30 | c | 7 |
| `OpenSpielMCTS:1000` | **0.40** | 0.39 | 0.37 | c | 7 |
| `MCTS:10000` | 0.36 | **0.37** | 0.32 | e | 10 |
| `OpenSpielMCTS:10000` | 0.34 | **0.37** | 0.33 | e | 11 |

The two MCTS agree. With 1000 playouts, `c` and `e` are close, and `c` is a little ahead: random playouts miss what North gets back after `c`. With 10 000 playouts, North's answers in the tree get good enough, `c` falls behind, and both play `e` like the alpha-betas. The only big difference is the time: our MCTS needs 4.3 seconds for 10 000 playouts here, OpenSpiel's 0.6 seconds.

## In Watch

```sh
.venv/bin/awale watch OpenSpielMCTS MCTS
.venv/bin/awale watch OpenSpielAlphaBeta:4 AlphaBeta:4
```

- **OpenSpielMCTS** shows its scores as shares of wins, like our MCTS, and its playouts in "Work done": about 1 400 in 0.1 s at the start of a game, where ours plays about 200.
- **OpenSpielAlphaBeta** shows the same scores as `AlphaBeta` at the same depth, and on a tie its choice is always the leftmost pit.
- While OpenSpiel's MCTS thinks, the window does not redraw. Its C++ code holds Python's lock (the GIL) until it is done, so our window's thread cannot run. With 0.1 s you hardly see it; with `OpenSpielMCTS:1s` the window stops for a second at each of its moves.

## What the tests check

- Replaying a game in OpenSpiel gives exactly our position, also when North moved first (then the board is turned around). A game set up by hand is refused.
- With only a position, both agents can think about the start position, whoever moves first.
- **OpenSpiel's alpha-beta gives every move the same score as our AlphaBeta**, at depths 1 to 4, with `store` and with `mix`, on positions from random games where no game ends inside the look-ahead.
- It takes the leftmost of equally good moves.
- Both agents take a win in one move, and OpenSpiel's alpha-beta scores it as `WIN`.
- OpenSpiel's MCTS: the playouts are counted, every score is a share from 0 to 1, the line starts with the move, the same seed gives the same thoughts, 1 playout still gives a legal move, and it stops when its time is up.
- `make_agent` builds both from their names, and both win a small tournament against Random, where they follow the random opening move by move.

## Tournaments

All tournaments use `--seed 1` and `--workers 4`. Games with a time limit are slow and not exactly repeatable, so those use few openings, and their intervals are wide.

### Alpha-beta: is our code right?

```sh
.venv/bin/awale tournament OpenSpielAlphaBeta:4 AlphaBeta:4 --seed 1 --workers 4
.venv/bin/awale tournament OpenSpielAlphaBeta:mix AlphaBeta:mix --openings 100 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `OpenSpielAlphaBeta:4` | `AlphaBeta:4` | 1000 | 460, 64, 476 | 49.2% ± 3.0% | +1.6 | 1.1 ms and 0.9 ms |
| `OpenSpielAlphaBeta:mix` | `AlphaBeta:mix` | 200 | 72, 12, 116 | 39.0% ± 6.6% | −2.3 | 9.4 ms and 8.8 ms |

- **At depth 4 with `store` they are even**, as they should be: the same scores for every move. OpenSpiel's is about as fast as ours. Its search is Python too, but it plays the moves in C++.
- **At depth 6 with `mix`, OpenSpiel's loses clearly: 39%.** Was something wrong? We followed 12 games move by move with both agents. They never gave a move a different score, except won and lost games (ours prefers a quick win and a slow loss). They chose different moves in about 1 position in 11, and almost always when several moves had the same best score: ours takes one of them at random, OpenSpiel's always the leftmost.
- **To check it, we gave our AlphaBeta OpenSpiel's habit.** With a small script outside the repository, our AlphaBeta took the leftmost of equal moves, and played the normal one: 39.5% ± 6.6%, the same as OpenSpiel's. So the code is right on both sides, and the rule for equal moves is worth about 10% of the points with `mix`.
- **Why is the leftmost pit worse?** We do not know yet. With `store` at depth 4 the habit cost nothing (49.2%). One guess: when the search cannot tell moves apart, the leftmost one is not a neutral choice. It is the same kind of move every time, and if that kind is a little worse on average, the small losses add up over a game. A random choice spreads them out. Testing this is a good experiment for later.

### MCTS: how much is speed worth?

```sh
.venv/bin/awale tournament OpenSpielMCTS:300 MCTS:300 --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament OpenSpielMCTS MCTS --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament OpenSpielMCTS AlphaBeta:4 --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament OpenSpielMCTS Deepening:mix --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament OpenSpielMCTS:1s Deepening:mix --openings 25 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `OpenSpielMCTS:300` | `MCTS:300` | 100 | 59, 9, 32 | 63.5% ± 9.0% | +3.0 | 12 ms and 95 ms |
| `OpenSpielMCTS` | `MCTS` | 100 | 97, 1, 2 | 97.5% ± 2.9% | +18.3 | 89 ms and 100 ms |
| `OpenSpielMCTS` | `AlphaBeta:4` | 100 | 96, 2, 2 | 97.0% ± 3.1% | +11.7 | 87 ms and 1.2 ms |
| `OpenSpielMCTS` | `Deepening:mix` | 100 | 7, 1, 92 | 7.5% ± 5.1% | −17.2 | 75 ms and 62 ms |
| `OpenSpielMCTS:1s` | `Deepening:mix` | 50 | 17, 1, 32 | 35.0% ± 13.2% | −7.3 | 715 ms and 63 ms |

- **With the same number of playouts, OpenSpiel's MCTS is a little better: 63.5%**, and 8 times faster. The MCTS-Solver is the likely reason: near the end of a game it knows which moves surely win or lose, where ours still trusts random playouts. Its C (1 on our scale, against our √2) may help a little too.
- **With the same time, it wins almost every game against ours: 97.5%.** 7 times more playouts are worth a lot: our MCTS with 10 times more time beat itself 96% (see [mcts.md](mcts.md)).
- **It beats `AlphaBeta:4` 97%**, where our MCTS got 23.5% with the same 0.1 s. A fast MCTS is a real player.
- **But it loses to `Deepening:mix`**: 7.5% with the same time. With 1 second per move, 11 times more time than Deepening, it gets 35%, still clearly behind. Speed alone does not make MCTS beat a good alpha-beta with a good heuristic: random playouts judge Awalé worse than `mix`. To catch up, MCTS would need smarter playouts or a heuristic (see the end of [mcts.md](mcts.md)).
- **It often thinks less than its time.** It averages 75–89 ms of its 0.1 s, and 715 ms of its 1 s: when the solver proves the result of every move, it stops early.

`Deepening:mix` stays the agent to beat.
