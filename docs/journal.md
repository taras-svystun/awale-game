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
