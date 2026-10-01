# MCTS

Code: `awale/agents/mcts_agent.py`. Tests: `tests/test_mcts_agent.py`.

MCTS stands for **Monte Carlo tree search**. Monte Carlo is the casino town: the name means "found by chance". It is a different kind of search from Minimax, AlphaBeta and Deepening, so you do not need [minimax.md](minimax.md) to read this. It helps to know [greedy.md](greedy.md), for the example position.

## The idea

### Judge a position by playing it out

Every search agent so far does two things: it looks a few moves ahead, then **guesses** how good each position there is with a [heuristic](heuristics.md) that we wrote. The heuristic is where our knowledge of Awalé lives: seeds count, mobility helps.

MCTS needs no heuristic. To judge a position, it **plays a random game from it to the end**, and looks at who won. One random game says almost nothing: random players give away seeds all the time. But play 1000 random games from the same position, and the share that South wins says something real. A position where South is far ahead is won by South in most random games too.

One random game to the end is a **playout**.

### First try: the same number of playouts for every move

The simplest version: for each legal move, play 1000 playouts from the position after it, and play the move with the best share of wins. This is called **flat Monte Carlo**. On the position from [greedy.md](greedy.md), South to move:

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

| Move | a | b | c | d | f |
|---|---|---|---|---|---|
| Seeds it captures | 0 | 2 | 0 | 0 | 2 |
| South's share of wins in 1000 playouts | 0.45 | 0.52 | 0.48 | 0.45 | 0.59 |

It picks `f`, the right move. But look at `b`: it captures 2 and gives North a capture of 5 (North's `F`, see [greedy.md](greedy.md)). Flat Monte Carlo thinks `b` is the second best move, a little better than even. Why? Because after `b`, a **random** North plays `F` only one time in four. Three times in four, North misses the capture. Flat Monte Carlo expects the opponent to play at random, and a real opponent does not.

It also wastes work: it spends as many playouts on `a` and `d`, which look bad early on, as on `f`.

### Grow a tree: spend the playouts where they matter

MCTS fixes both. It grows a **tree** of positions, one node per position, starting from the position on the board. Each node remembers two numbers: how many playouts went through it (**visits**), and how many of those the player who moved into it won (**wins**). Each playout has four steps:

1. **Selection.** Start at the top. At each node, go down to the child that looks best (see the formula below). Stop at a node that has a legal move nobody tried yet.
2. **Expansion.** Try one of those untried moves, chosen at random, and add the position it leads to as a new node.
3. **Playout.** From the new node, play random moves until the game ends.
4. **Backpropagation.** Go back up from the new node to the top. Every node on the way gets one more visit, and one more win if the player who moved into it won the playout (a draw counts as half a win).

Then repeat, as many times as there is time for. Each playout adds exactly one node to the tree.

The key is step 1. Inside the tree, **each player chooses their own best move**: at South's nodes, the child with the best share for South, at North's nodes, the child with the best share for North. So after `b`, once North's `F` has won a few playouts, North chooses `F` again and again, and `b`'s share of wins falls. The opponent in the tree is no longer random: the more playouts, the better it plays. With endless playouts, MCTS chooses the same move as Minimax would with endless depth.

And because the selection prefers good moves, good moves get most of the playouts, and their part of the tree grows deepest. MCTS has no fixed depth: the tree is deep where it matters and shallow where it does not.

### Which child: the UCB formula

Should the selection always go to the child with the best share of wins? No. After the first few playouts, a good move may have lost twice by bad luck, and would never be tried again. We must also **explore**: try the moves we know little about. But not too much, or we waste playouts on bad moves.

This is the problem of a gambler in front of a row of slot machines, each paying out with a different, unknown chance: keep playing the machine that paid best so far, or try the others? The **UCB** formula (Upper Confidence Bound) is a good answer to it, and MCTS uses it at every node:

```
UCB = share of wins + C × √( ln(parent's visits) / child's visits )
```

- **The share of wins** (wins / visits) is how good the move looks so far.
- **The bonus** on the right is big for a child with few visits, and shrinks fast as it gets visited. It grows slowly (with the logarithm, `ln`) as the parent is visited more, so a move that was left alone for long gets tried again now and then.
- **C** says how much to explore. We use √2 ≈ 1.41, the textbook value for results from 0 to 1. See [the tournaments](#tournaments) for other values.

An example from the tests. The parent was visited 100 times. One child was visited 90 times and won 60%; the other 10 times and won 40%:

- the good child: 0.60 + 1.41 × √(ln 100 / 90) = 0.60 + 0.32 = **0.92**
- the rare child: 0.40 + 1.41 × √(ln 100 / 10) = 0.40 + 0.96 = **1.36**

So the rare child is tried again. If it keeps losing, its share stays low while its bonus shrinks, and soon the good child wins the formula again.

### Which move to play: the one tried most

When the time is up, MCTS plays the move with the **most visits**, not the best share of wins. A move tried 3 times and won 3 times has a share of 1.00, but it may just have been lucky. The move tried most is the one the selection kept coming back to, through hundreds of playouts. Usually it also has the best share.

## How the code works

Two classes: `Node` holds one position of the tree, and `MCTSAgent` grows the tree and chooses the move.

### `Node`

```python
class Node:
    def __init__(self, position, move=None, parent=None):
        self.position = position
        self.move = move
        self.parent = parent
        self.children = []
        self.untried = [] if position.ends_game() else position.legal_moves()
        self.visits = 0
        self.wins = 0.0

    @property
    def win_share(self):
        return self.wins / self.visits
```

- `move` is the pit played in the parent's position to get here, so we know which move a child of the top node stands for.
- `untried` starts with all legal moves. The expansion step takes them out one by one. A node with no untried moves left is **fully expanded**: every legal move has its child.
- `wins` counts points for the player who **played** `move`, the one who chose to come here. That is the player whose choice the selection step makes from the parent, so it is the share that player wants high. Who that is, South or North, changes at every level of the tree.
- `__slots__` in the real code saves memory: the tree can have thousands of nodes.

### `grow_tree`: the four steps

```python
def grow_tree(self, position):
    started = time.perf_counter()
    self.positions = 0
    root = Node(position)
    while root.untried or not self.is_done(root.visits, started):
        # 1. Selection
        node = root
        while not node.untried and node.children:
            node = self.select(node)
        # 2. Expansion
        if node.untried:
            move = node.untried.pop(self.rng.randrange(len(node.untried)))
            child = Node(node.position.play(move), move, node)
            node.children.append(child)
            node = child
            self.positions += 1
        # 3. Playout
        end = self.playout(node.position)
        # 4. Backpropagation
        while node.parent is not None:
            node.visits += 1
            node.wins += points(end, node.parent.position.to_move)
            node = node.parent
        root.visits += 1
    return root
```

- **The loop** runs until `is_done`: the number of playouts or the time is used up, whichever comes first. `root.untried` keeps it going until every legal move has been tried once, so every move gets a score even with almost no time.
- **Selection** goes down while the node is fully expanded (`not node.untried`) and has children. It stops at a node with untried moves, or at a node where the game ends (no untried moves and no children).
- **Expansion** pops a random untried move. Random, not the leftmost, so that with few playouts the left pits are not favoured. Where the game ends, there is nothing to expand, and the playout starts right there.
- **Backpropagation** walks up through `parent`. `points(end, side)` is 1 if `side` won the playout, 1/2 for a draw, 0 for a loss. Each node adds the points of the player who moved into it: `node.parent.position.to_move`. The top node has no parent and no mover, so it only counts visits.

### `select`: the UCB formula

```python
def select(self, node):
    log_visits = math.log(node.visits)
    return max(
        node.children,
        key=lambda child: child.win_share + self.exploration * math.sqrt(log_visits / child.visits),
    )
```

This is the formula from [the idea](#which-child-the-ucb-formula), with `self.exploration` as C. Every child has at least one visit here (the playout that started when it was added), so there is no division by zero.

### `playout`: one random game

```python
def playout(self, position):
    for _ in range(PLAYOUT_MOVES):        # 200
        moves = position.legal_moves()
        if not moves or max(position.stores) >= WINNING_STORE:
            break
        position = position.play(self.rng.choice(moves))
        self.positions += 1
    return position.with_rows_collected()
```

- The check at the top is `position.ends_game()`, written out so it asks for the legal moves only once per move. A playout is almost all of MCTS's work, and this makes it about a quarter faster.
- `PLAYOUT_MOVES` stops a random game after 200 moves. A random game from the start lasts about 110 moves, but a few go round in circles for a very long time. A position does not know the earlier positions, so a playout cannot see a [repetition](../../CONTEXT.md).
- `with_rows_collected` gives the seeds left on the board to each row's owner, as at the end of a real game, so a playout stopped at 200 moves is judged by who has more seeds.

### `think`: the move, the scores, the line

```python
def think(self, position):
    root = self.grow_tree(position)
    most = max((child.visits, child.win_share) for child in root.children)
    move = self.rng.choice(sorted(c.move for c in root.children if (c.visits, c.win_share) == most))
    scores = {child.move: child.win_share for child in sorted(root.children, key=lambda child: child.move)}
    deepest = max(depth for depth, _ in self.walk(root))
    return Thoughts(move, scores, self.expected_line(root, move), self.positions, deepest, playouts=root.visits)
```

- **The move**: the most visits; on a tie, the better share of wins; on a tie of both, a random choice.
- **The scores** are the share of wins of each move, from 0 to 1, for the player to move. Watch shows them with two decimals: `0.58`.
- **The depth** is the deepest node of the tree. Playouts go much deeper, to the end of the game, but they play at random, so they are not "looking ahead".
- **The expected line** (`expected_line`) starts with the chosen move, then follows the child with the most visits, and so on. It stops at a child visited only once: one random game is not something the players "expect".
- **Work done** counts the playouts, and every position played in them and added to the tree.

### Its name: playouts and time

`make_agent` reads the options after the colons in any order: a whole number is the number of playouts per move, and a number with an `s` is the time per move in seconds. MCTS takes no heuristic and no depth.

| Name | Playouts per move | Time limit |
|---|---|---|
| `MCTS` | no limit | 0.1 s |
| `MCTS:1s` | no limit | 1 s |
| `MCTS:1000` | 1000 | none |
| `MCTS:1000:1s` | 1000 | 1 s, whichever comes first |

With a number of playouts and no time, the same seed always gives the same move, so a tournament can be repeated exactly. With a time limit, the number of playouts depends on how busy the computer is.

## An example on a real position

The position from [greedy.md](greedy.md), [minimax.md](minimax.md) and [deepening.md](deepening.md): South to move, stores 0 and 0.

```
South: 5 5 5 5 0 1     North: 1 7 7 0 6 6
```

Here is how the tree of `MCTS:3000` (seed 0) grows. Each cell is the move's visits / South's share of wins:

| Playouts | a | b | c | d | f | Deepest node |
|---|---|---|---|---|---|---|
| 5 | 1 / 1.00 | 1 / 1.00 | 1 / 0.00 | 1 / 0.00 | 1 / 0.00 | 1 |
| 20 | 5 / 0.60 | 5 / 0.60 | 4 / 0.38 | 4 / 0.25 | 2 / 0.00 | 2 |
| 100 | 11 / 0.27 | 13 / 0.31 | 25 / 0.58 | 19 / 0.50 | 32 / 0.69 | 4 |
| 300 | 37 / 0.38 | 35 / 0.43 | 73 / 0.53 | 42 / 0.40 | 113 / 0.62 | 5 |
| 1000 | 126 / 0.41 | 116 / 0.40 | 151 / 0.44 | 133 / 0.42 | 474 / 0.58 | 6 |
| 3000 | 256 / 0.42 | 331 / 0.45 | 293 / 0.43 | 186 / 0.37 | 1934 / 0.58 | 8 |

Follow it down:

- **5 playouts.** Each move is tried once, one random game each. `f`, the best move, lost its first game. One playout is pure luck.
- **20 playouts.** `f` lost its first two games, so UCB gives it only 2 of the 20. Its bonus keeps growing while the others are visited.
- **100 playouts.** `f` won enough to take the lead, and the selection comes back to it more and more: 32 visits, then 113, then 474. The other moves still get playouts now and then, from their bonus.
- **1000 and 3000.** `f` gets about half, then two thirds, of all playouts. Its share settles near 0.58: in a random game from here, South wins a bit more than half the time.

Now look inside the tree under `b`, after 1000 playouts. These are North's answers, with North's share of wins:

| North's answer to b | B | C | E | F |
|---|---|---|---|---|
| Visits / North's share | 20 / 0.45 | 23 / 0.52 | 17 / 0.41 | **55 / 0.76** |

The tree found North's capture: `F` wins 76% for North, and North's selection chooses it in half the playouts through `b`. That is why `b` falls to 0.40 for South, below flat Monte Carlo's 0.52. Nobody told MCTS that captures matter. It found out from the playouts.

`MCTS:1000` plays `f`, and expects the line `f C c D e`. That line is only followed while each move was tried more than once, so it is short and less sure the further it goes.

## In Watch

```sh
.venv/bin/awale watch MCTS Deepening:mix
```

- **Move scores**: the share of its playouts won after each move, from `0.00` to `1.00`. Its choice, in yellow, is the move it tried most. It is almost always the best share too.
- **Expected line**: the moves tried most, one after another, while they were tried more than once.
- **Work done**: about 200 playouts in its 0.1 seconds at the start of a game, and thousands near the end, where playouts are short. Each playout plays many moves, so it counts tens of thousands of positions. The depth is the deepest node of the tree.

With 1 second per move, it plays 10 times more playouts:

```sh
.venv/bin/awale watch MCTS:1s MCTS
```

Near the end of a game you will see scores like `1.00` for every move: every random game from here is won. And `0.00`: every one is lost.

## What the tests check

- Every playout goes through the top of the tree and adds one node. Each node's visits are 1 (its own playout) plus its children's visits, and its wins are between 0 and its visits.
- The same seed and the same number of playouts give the same thoughts.
- The thoughts: a share of wins from 0 to 1 for every legal move, the line starts with the move, and the playouts are counted.
- It plays the move tried most, and the expected line follows the answers tried most.
- UCB: with C = 0 it takes the best share; with C = √2 it tries a child with few visits again (the example above).
- A playout ends the game and collects the seeds left on the board; a win is worth 1 point, a draw 1/2.
- It takes a win in one move, and with 1000 playouts it does not fall into Greedy's trap above, from three different seeds.
- With a time limit it stops in time, and with almost no time it still tries every move once.
- It plays whole games, and `MCTS:30` wins all 4 games of a small tournament against Random.
- The names: `MCTS` thinks for 0.1 s, `MCTS:1000` has no time limit, `MCTS:2s:500` sets both, and a depth, a heuristic or a playout count of 0 are refused.

## Tournaments

All tournaments use `--seed 1` and `--workers 4`. MCTS with a time limit is not exactly repeatable, even with the same seed: how many playouts it gets depends on how busy the computer is. Games with 0.1 s or 1 s per move are slow, so these use few openings, and the intervals are wide.

**With 0.1 seconds per move**, the same time as `Deepening:mix`:

```sh
.venv/bin/awale tournament MCTS Greedy --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament MCTS AlphaBeta:4 --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament MCTS AlphaBeta:mix --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament MCTS Deepening:mix --openings 50 --seed 1 --workers 4
.venv/bin/awale tournament MCTS MCTS --openings 50 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `MCTS` | `Greedy` | 100 | 96, 2, 2 | 97.0% ± 3.1% | +14.7 | 100 ms and 24 µs |
| `MCTS` | `AlphaBeta:4` | 100 | 18, 11, 71 | 23.5% ± 7.7% | −11.6 | 100 ms and 1.0 ms |
| `MCTS` | `AlphaBeta:mix` | 100 | 2, 0, 98 | 2.0% ± 2.8% | −23.6 | 100 ms and 14 ms |
| `MCTS` | `Deepening:mix` | 100 | 0, 0, 100 | 0.0% | −24.8 | 100 ms and 61 ms |
| `MCTS` | `MCTS` | 100 | 39, 5, 56 | 41.5% ± 9.5% | −2.7 | 100 ms and 100 ms |

- **It beats Greedy easily**, about as well as `Minimax:2` does (99%, see [minimax.md](minimax.md)). The tree sees the opponent's captures, like the trap above.
- **It loses to every AlphaBeta**, even to plain `AlphaBeta:4`, which thinks 100 times less. With `mix`, AlphaBeta and Deepening win almost every game. In 0.1 s our MCTS plays only a few hundred playouts early in the game, too few to judge moves well. And a heuristic that knows Awalé is worth a lot of random games.
- **Against itself it is even**: the interval includes 50%.

**With 1 second per move**, 10 times more playouts:

```sh
.venv/bin/awale tournament MCTS:1s MCTS --openings 25 --seed 1 --workers 4
.venv/bin/awale tournament MCTS:1s AlphaBeta:4 --openings 25 --seed 1 --workers 4
.venv/bin/awale tournament MCTS:1s Deepening:mix --openings 25 --seed 1 --workers 4
```

| A | B | Games | A wins, draws, losses | A's points | Seeds, A minus B | Time per move, A and B |
|---|---|---|---|---|---|---|
| `MCTS:1s` | `MCTS` (0.1 s) | 50 | 48, 0, 2 | 96.0% ± 5.5% | +18.9 | 1.00 s and 100 ms |
| `MCTS:1s` | `AlphaBeta:4` | 50 | 41, 3, 6 | 85.0% ± 9.4% | +6.0 | 1.00 s and 0.8 ms |
| `MCTS:1s` | `Deepening:mix` (0.1 s) | 50 | 3, 0, 47 | 6.0% ± 6.6% | −20.1 | 1.00 s and 61 ms |

- **More playouts make it much stronger.** 10 times more time wins 96% of the points against itself. Each extra move of depth gave AlphaBeta about 76% (see [minimax.md](minimax.md)), so 10 times more playouts is worth more than one move of depth.
- **With 1 s it beats `AlphaBeta:4`**, which lost 23.5% to it with 0.1 s. So MCTS is not wrong, only slow: it needs many playouts.
- **It still loses to `Deepening:mix`**, while thinking 16 times longer per move. With our Python speed and random playouts, MCTS is far from the best AlphaBeta with a good heuristic. `Deepening:mix` stays the agent to beat.

**The exploration constant C.** We tried other values of C against √2, with 300 playouts per move (so the games can be repeated exactly), 100 games each, using a small script outside the repository:

| C | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Points against C = √2 | 57.0% ± 9.3% | 63.5% ± 9.2% | 45.5% ± 9.6% |

C = 1.0 looked better, so we played 200 more games with other openings (`--seed 2`): 53.8% ± 6.8%, which cannot tell the two apart. So we kept the textbook √2. To try a value yourself:

```python
from awale.agents import MCTSAgent
from awale.engine import Position

MCTSAgent(seed=0, playouts=1000, exploration=1.0).think(Position.start())
```

## Why it is weak here, and what could make it stronger

Two things hold our MCTS back:

1. **Python is slow at playouts.** We play about 1 500 random games per second from the start position. MCTS programs written in C++ play hundreds of thousands. OpenSpiel's MCTS (step 12) will show how much the speed alone is worth.
2. **Random playouts are a poor judge of Awalé.** A random player misses most captures and gives seeds away all the time. A position that a good player wins in 10 moves is often lost in a random game. A heuristic like `mix` knows that mobility and seeds matter; a random game has to find it out, one playout at a time.

Ideas that are known to help, if we want to come back to MCTS:

- **Smarter playouts**: play like Greedy in the playouts, taking captures when there are some, instead of moving at random. Each playout is slower but tells more.
- **Shorter playouts with a heuristic**: play 10 random moves, then judge the position with `mix` instead of playing to the end. This mixes MCTS with what we learned in step 9. AlphaZero goes all the way: no playouts at all, and a neural network judges each new node.
- **Keep the tree**: after our move and the opponent's answer, the part of the tree under them is still good. Today we throw it away and start again for every move.
- **Proven wins** (MCTS-Solver): when a node's game is surely won or lost, mark it so, and never spend playouts on it again.
