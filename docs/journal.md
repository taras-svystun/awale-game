# Journal

A short, plain-English history of each finished step: what we did, why, and how. Newest at the bottom.

## Step 0: research and planning (2026-09-30)

**What:** We looked at the rules of Awalé and at existing code. We wrote the glossary (`CONTEXT.md`), the plan (`docs/PLAN.md`) and the first decision record (`docs/adr/0001`).

**Why:** We wanted to agree on the rules and on the words we use before writing any code, so the code, the docs and our conversations all mean the same thing.

**How:** We checked Wikipedia, French rule sheets, OpenSpiel, pyAwale and the `mancala` package on PyPI. There is no good Python Awalé with a UI or AI we could reuse. OpenSpiel has correct rules but they are written in C++, so we write our own engine in Python and use OpenSpiel to check it.

## Step 1: the game engine (2026-09-30)

**What:** `awale/engine.py` holds all the rules. `Position` is one moment of the game and knows how to play one move. `Game` keeps the whole game, knows when it ends, and can undo. There is no window yet.

**Why:** Everything else (the window, the AI agents, tournaments) is built on these rules, so they must be right first. The engine has no Pygame in it, so a web version can use it later too.

**How:**
- We wrote the tests first, one rule at a time, on small positions worked out by hand: sowing, skipping a pit with 12+ seeds, capture chains, grand slam, feeding, end of game, undo.
- Then we played 2000 random games in our engine and in OpenSpiel side by side and compared every move. Those games include 129 grand slams, 182 repetitions and more than 1000 feeding positions, so even the rare rules are checked.
- The comparison found one difference, and we changed our rules to match OpenSpiel: when a game ends because someone reached 25, the seeds left on the board also go to the owner of each row. The winner stays the same, but the final score now always adds up to 48.

## Step 2: Play for two people (2026-09-30)

**What:** `awale play` opens a Pygame window where two people take turns on one computer. You click a pit or press 1-6. Pits you cannot play are dimmed, the last move has an orange ring, and captures and the final result are shown at the top.

**Why:** It is the first way to actually play the game, and the window code is the base for Play against AI and Watch later.

**How:**
- `awale/ui/board_view.py` knows where each pit is on the screen and draws the board. North's pit 1 is at the top right, so sowing goes counter-clockwise on the screen, as on a real board.
- `awale/ui/play.py` turns clicks and keys into moves on the engine's `Game`. Only this folder imports Pygame.
- `awale/cli.py` is the `awale` command, with one subcommand per way to use the game. Only `play` exists for now.
- The tests send fake clicks and key presses to the window with no real screen (SDL's "dummy" video driver).
- Undo and the start menu come in step 3, together with Play against AI.

## Step 3, part 1: agents and Play against AI (2026-09-30)

**What:** The start menu, Play against an AI agent, and Undo. The `Agent` interface and an empty `RandomAgent`, with its tests ready. Taras writes `RandomAgent.choose_move` in part 2, which finishes the step.

**Why:** Every AI we build later (Greedy, Minimax, alpha-beta, MCTS) plugs into the same `Agent` interface, so the window, Watch and Tournament never need to know how an agent thinks. Taras writes the first agents himself to learn the ideas, so the code around them is ready first.

**How:**
- `awale/agents/` has `Agent`, with one method: `choose_move(position)` returns a pit 1-6. `AGENTS` lists the agents the menu can offer. This folder never imports Pygame, and a test checks that.
- The AI thinks in a background thread (`awale/ui/agent_thread.py`), so the window keeps drawing. Its move waits at least 0.7 seconds, so you can see your own move land first. If the agent crashes, the error is raised in the window instead of the game waiting forever.
- Undo goes back to the last position where a person was to move. Between two people that is one move. Against an AI it takes back the AI's move and yours. If the AI is still thinking, its answer is thrown away.
- `awale/ui/menu.py` is the start menu. It does not start a game with no person, because AI against AI is Watch (step 5).
- `Game.positions` is new: every position so far, which Undo needs.
- The window tests use small fake agents (one always plays its leftmost pit, one waits until the test lets it answer), so they do not depend on Random.

## Step 3, part 2: the Random agent (2026-09-30)

**What:** `RandomAgent.choose_move` picks any legal move, each with the same chance. Its tests now run, and `docs/agents/random.md` explains how it works. This finishes step 3.

**Why:** We changed how we work: Claude now writes every agent and explains it in detail, instead of Taras writing Random, Greedy and Minimax. Random is the baseline that every later agent must beat.

**How:**
- One line: `self.rng.choice(position.legal_moves())`. The rules live in `legal_moves`, so the agent never needs to know them.
- The agent has its own random generator, so the same seed always gives the same game.
- A quick run of 2000 games of Random against Random: North won 977, South 891, 132 draws. The tournament in step 4 will measure this properly.
- From now on, every agent gets its own explanation in `docs/agents/`.

## Step 4: tournament and game records (2026-09-30)

**What:** `awale tournament A B` plays many games between two AI agents with no window and prints who is stronger. Finished Play games are saved as game records in `records/games`, and `--save` writes a tournament's games to a CSV in `records/tournaments`.

**Why:** From step 6 on, every new agent must prove it beats the ones we have. Watching a few games is not enough: luck decides a lot, so we need many games and a number that says how sure we are. Game records let us look at any game again later.

**How:**
- `awale/tournament.py` makes 500 different random openings of 6 moves and plays each twice, with the agents swapping sides. Random against Random showed why: North wins clearly more often than South, so each agent must get each side equally often.
- The report gives A's points (a win is 1, a draw 1/2) with a 95% confidence interval: the average ± 1.96 standard errors. If the interval includes 50%, the games cannot tell the agents apart.
- The games run in one process per CPU core. All random choices (openings and each agent's seed) are made before the games start, so the same `--seed` gives the same games on any number of cores. For that, every agent now gets its own seeded random generator from `Agent`.
- Random against Random over 10000 games: A's points 50.5% ± 1.0%, as it should be for two equal agents.
- `awale/records.py` writes moves as a-f for South and A-F for North, saves one JSON file per game, and keeps only the newest 100 games and 10 tournaments. `GameRecord.replay()` plays a record back into a `Game`.
- Tests never write into the real `records/` folder: `tests/conftest.py` points it to a temporary folder.

## Step 5: Watch with the thoughts panel (2026-09-30)

**What:** `awale watch A B` opens a window where two AI agents play each other. You can pause, step one move at a time, and set the speed with a slider. A thoughts panel shows what the agent to move is thinking: a score over each pit it may play, the line of play it expects, and the work it did (positions, depth, time). Each part has a checkbox. The start menu now opens Watch when both sides are AI agents.

**Why:** From step 6 on we write agents that look ahead. Watching their thoughts on a real position is the quickest way to see why an agent plays a move, and to spot a bug in its scores before a tournament hides it in an average.

**How:**
- `Thoughts` (in `awale/agents/base.py`) holds the move and, if the agent has them, the move scores, the expected line, the positions it looked at and the depth. An agent writes either `choose_move` (just the move, like Random) or `think` (the move with its thoughts). Each method is built from the other, and making an agent class with neither is an error at once, instead of an endless loop later.
- Play and Watch now share `GameScreen` (`awale/ui/game_screen.py`): the game, the agents, the background thread, the messages and the game record. `PlayScreen` adds clicks and Undo, `WatchScreen` adds pause, step and speed.
- In Watch, an agent's thoughts are shown on the position it thought about, before its move is played. The wait is counted from when it finished thinking, so a slow agent's thoughts stay on screen as long as a fast agent's.
- The speed slider goes from 3 s to 0.1 s per move on a log scale, like a volume knob. Faster than 0.1 s is not possible: the window draws 30 frames a second, and a move takes two frames.
- `awale/ui/thoughts_view.py` draws the panel, and `awale/ui/widgets.py` has the new checkbox and slider. The window is taller (680 px) to make room; Play will use that room for its own thoughts panel later.
- The window tests use a small fake agent that scores each pit by its number, since no real agent gives scores yet.

## Step 6: the Greedy agent (2026-09-30)

**What:** `GreedyAgent` tries every legal move and plays the one that captures the most seeds. `docs/agents/greedy.md` explains it. It is in the start menu, Watch and Tournament.

**Why:** It is the simplest agent that looks ahead, one move deep, and the first one that really plays. Minimax (step 7) builds on the same idea and must beat it.

**How:**
- The score of a move is how much our store grows after it. The engine applies the rules, so a grand slam scores 0.
- When several moves capture the same, Greedy picks one of them at random. With `max` it would always play its leftmost pit when nothing can be captured, which is 69% of its moves.
- Its thoughts: the capture for each move, the line is just its own move, depth 1, one position per legal move.
- Greedy against Random, 10000 games: 92.8% ± 0.5% of the points, 20 seeds ahead on average. Greedy against Greedy: 50.2% ± 1.0%, even as it should be.
- Its weakness: it never looks at the opponent's answer, so it takes 2 seeds and gives away 5. `greedy.md` shows this on a real position.

## Step 7: the Minimax agent (2026-09-30)

**What:** `MinimaxAgent` looks 4 moves ahead, expecting the opponent to answer with their best move, and judges the positions where it stops with the `store_diff` heuristic: my store minus theirs. `docs/agents/minimax.md` explains it. It is in the start menu, Watch and Tournament, and on the command line `Minimax:6` sets its depth.

**Why:** Greedy never looks at the opponent's answer, so it takes 2 seeds and gives away 5. Minimax is the classic fix, and the base for alpha-beta (step 8), which must choose the same moves faster, and for better heuristics (step 9).

**How:**
- `minimax` calls itself one move deeper for each legal move: on our turns it takes the highest value, on the opponent's the lowest. It also returns the line of play that leads to the value, which Watch shows as the expected line.
- A position where the game ends is not guessed: the seeds left go to each row's owner, and a win is worth 100 plus the depth still left, so a win beats any seed count and a quick win beats a slow one. `Position.ends_game()` is new, and `Game` uses it too, so both agree on when a game ends. The search does not see repetitions.
- Heuristics live in `awale/agents/heuristics.py`, apart from the search, so step 9 can give Minimax other ones.
- `make_agent("Minimax:6")` builds an agent from a name with a depth. The tournament, `awale watch` and the menu all use it, and the name with its depth goes into game records. The menu buttons moved left to make room for a fourth one.
- Tournaments: `Minimax:2` wins 99.2% ± 0.2% of the points against Greedy over 10000 games, so just looking at the answer fixes Greedy. Against itself each extra move of depth wins clearly: depth 4 gets 77.6% against depth 2, depth 6 gets 83.5% against depth 4, but thinks 20 times longer (63 ms against 3 ms per move). That is the case for alpha-beta. Minimax against Minimax: 50.9% ± 1.5%, even.

## Step 8: the AlphaBeta agent (2026-09-30)

**What:** `AlphaBetaAgent` is Minimax with alpha-beta pruning: it stops looking at a move as soon as it is proved worse than one it already has. It looks 6 moves ahead by default. `docs/agents/alphabeta.md` explains it. It is in the start menu, Watch and Tournament, and `AlphaBeta:8` sets its depth.

**Why:** Each move of depth wins clearly, but Minimax's time grows 4–5 times per move of depth. Alpha-beta gives exactly the same moves for far less work, so we can afford to look deeper.

**How:**
- `AlphaBetaAgent` is a subclass of `MinimaxAgent` and replaces only the search: `alphabeta` carries a window (alpha, beta) down the tree and stops when alpha ≥ beta. It only replaces its best move with a strictly better one, so on a tie it keeps the leftmost pit, like Minimax, and gives the same expected line.
- At the top, every one of our moves is searched with the widest window, so it gets its exact score. Watch then shows the same scores as Minimax, and a tie between the best moves is broken at random in the same way. This costs about a third more positions at depth 6 than a textbook alpha-beta, and gives exactly Minimax's thoughts.
- The tests check that its thoughts are exactly Minimax's on many positions, that whole games and a tournament come out the same, and the promise of the window: a value inside it is exact, one outside is a bound.
- From the start position it looks at 7 times fewer positions than Minimax at depth 6, and 30 times fewer at depth 8. In tournaments with the same seed it plays exactly Minimax's games: `AlphaBeta:6` and `Minimax:6` against Greedy both win 497, draw 2 and lose 1, at 14 ms and 95 ms per move.
- The saved time buys depth: `AlphaBeta:8` against `Minimax:6`, with about the same time per move, gets 81.0% ± 3.3% of the points. AlphaBeta against itself: 50.2% ± 2.1%, even.
- The start menu now has five agents in a row, so the buttons are narrower.

## Step 9: better heuristics (2026-10-01)

**What:** Four board features in `awale/agents/heuristics.py`: seeds in my row, weak pits with 1–2 seeds, mobility (pits I can play) and big pits with 12+ seeds. `weighted` adds them to `store_diff` with weights. Minimax and AlphaBeta take a heuristic by name after a colon: `AlphaBeta:mix`, `AlphaBeta:8:mix`. The start menu has an `AlphaBeta:mix` button. `docs/agents/heuristics.md` explains it all.

**Why:** Most positions where the search stops are quiet, and `store_diff` scores them all the same, so the search picks among them at random. A heuristic that looks at the board can tell them apart.

**How:**
- Each feature is "mine minus the opponent's". Tournaments at depth 4 (1000 games, `--workers 4`) chose the weights. Mobility alone at 0.5 wins 96.6% of the points against `store_diff`; seeds in my row help only with a small weight (0.1: 87.6%). Weak pits hurt with the sign we expected, and big pits changed nothing, so both are left out of `mix`.
- `mix` = `store_diff` + 0.5 × mobility + 0.1 × row seeds. It beats mobility alone 67.2% ± 2.8%. What it learned: do not feed the opponent, keep its empty pits empty.
- At depth 6, `AlphaBeta:mix` wins 95.5% ± 1.7% against `AlphaBeta`. Even `AlphaBeta:4:mix` beats `AlphaBeta` at depth 6 (82.2%) with 3.6 times less time per move, and `AlphaBeta:mix` beats `AlphaBeta:8` (82.0%).
- The default heuristic is still `store`, so `AlphaBeta` still plays exactly like `Minimax` at the same depth.
- Weighted values are rounded to 6 decimals, since 0.1 × 3 is not exactly 0.3 in binary and equal positions must tie. A test checks that no heuristic can reach the value of a won game.
- New rule in `CLAUDE.md`: tournaments use AlphaBeta, not Minimax, and Minimax at depth 5 or more needs Taras's OK, because long tournaments heat the laptop.

## Step 10: the Deepening agent (2026-10-01)

**What:** `DeepeningAgent` is AlphaBeta with move ordering, iterative deepening and a time limit. It searches 1 move deep, then 2, then 3, ..., and when its time is up (0.1 s per move by default) it plays the best move of the deepest search it finished. `Deepening:0.5s`, `Deepening:8` and `Deepening:12:1s:mix` set its time, its depth or both. The start menu has `Deepening:mix`. `docs/agents/deepening.md` explains it.

**Why:** Alpha-beta skips more when it tries the best move first, and trying pits left to right is just luck. A fixed depth takes 5 ms in one position and 2 s in another; a time limit is what a person playing it, and a fair tournament, want.

**How:**
- `ordered_moves` tries first the move that was best in this position in the last, shallower search (`best_moves`, a dict with positions as keys), then the moves that capture most, like Greedy.
- At the top it uses a narrow window: every move after the first only has to be proved worse than the best so far, and gets an upper bound. Watch shows those scores with "≤". The window starts a hair (`TIE`) below the best score, so a move that ties still gets its exact score, and the random choice between equal moves is the same as AlphaBeta's. Scores never differ by less than 0.000001 because heuristics round to 6 decimals.
- The narrow window is where most of the saving comes from. We measured the parts one by one: ordering with the widest window at the top saved little, and iterative deepening alone costs more than it saves.
- When the time is up, `OutOfTime` is raised deep in the search and caught in `think`. It does not start a depth when more than half the time is gone, and stops early when every line ends the game or the game is surely won or lost.
- At a fixed depth it chooses exactly AlphaBeta's moves: the tests check this on many positions, whole games and a tournament. Tournaments with the same seed give the same results, 1.6 times faster at depth 6 and 2.6 times at depth 8. At depth 10 with `mix` it is almost 5 times faster.
- With 0.1 s per move, `Deepening:mix` gets 79.0% ± 5.4% of the points against `AlphaBeta:mix` and 64.2% ± 6.5% against `AlphaBeta:8:mix`, which thinks about as long. With 0.4 s it gets 83% against itself at 0.1 s. Time-limited tournaments are not exactly repeatable, since the depth reached depends on how busy the computer is.
- `Thoughts` has a new `upper_bounds` field. The menu buttons are narrower to fit seven. `CONTEXT.md` now defines depth and time limit.

## Step 11: the MCTS agent (2026-10-01)

**What:** `MCTSAgent` is Monte Carlo tree search. It judges a move by playing random games to the end (playouts) and counting who won, and it grows a tree so that good moves, and good answers to them, get most of the playouts. It thinks for 0.1 s per move by default; `MCTS:1s` sets the time, `MCTS:1000` the number of playouts. It is in the start menu, Watch and Tournament. `docs/agents/mcts.md` explains it.

**Why:** Every agent so far looks a fixed number of moves ahead and then guesses with a heuristic we wrote. MCTS is the other big family of game search: no heuristic and no fixed depth, only random games. It is also what step 12 compares with OpenSpiel's MCTS.

**How:**
- Each playout has four steps: selection with the UCB formula (share of wins plus a bonus for moves tried less, C = √2), expansion of one untried move, a random playout, and backpropagation. Each node counts wins for the player who moved into it. It plays the move tried most.
- Every legal move is tried at least once, so every move gets a score. A playout stops after 200 moves, since a few random games go round in circles. It asks for the legal moves once per move, which makes playouts a quarter faster: about 1 500 per second from the start.
- `make_agent` now has `OPTIONS`: what each agent can set after a colon. For MCTS a whole number is the playouts, not a depth. Errors say what the agent can set.
- `Thoughts` has a new `playouts` field. Watch shows MCTS scores as shares of wins with two decimals (`0.58`, `1.00`), and the playouts in "Work done". The menu has eight buttons now, so they are narrower, with a smaller font.
- `CONTEXT.md` defines a playout.
- Tournaments (`--workers 4`, 50–100 games each, so the intervals are wide): with 0.1 s per move it beats Greedy 97.0%, but loses to plain `AlphaBeta:4` (23.5%) and wins nothing against `Deepening:mix`. With 1 s it beats itself at 0.1 s 96.0% and `AlphaBeta:4` 85.0%, but still gets only 6.0% against `Deepening:mix`. It needs many playouts, and Python plays only about 1 500 per second; random playouts also judge Awalé much worse than `mix`.
- Other values of C (0.5, 1.0, 2.0) did not beat √2 clearly, so it stays.
