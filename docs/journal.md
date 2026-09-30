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
