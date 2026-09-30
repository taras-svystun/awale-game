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
