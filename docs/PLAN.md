# Plan

Words in **bold** are defined in `../CONTEXT.md`.

## What we agreed

**Rules.** Awalé ("abapa" rules), the same as OpenSpiel's `oware`:
- 4 seeds per pit at the start;
- a pit with 12+ seeds skips itself when sowing;
- capture 2 or 3, going back in a chain;
- a **grand slam** captures nothing;
- you must **feed** an empty opponent;
- 25 seeds wins, and 24–24 is a draw;
- a **repetition** ends the game and each player takes their own row.

**Tech.**
- Python 3.11 with a plain `venv` and `pip`, `pytest` for tests, Pygame for the window.
- Our own engine in plain Python, checked against OpenSpiel on thousands of random games (see `adr/0001`).
- The engine and the agents never import Pygame, so a web version can be added later as just another front end.

**Play** (window):
- two people on one computer, or a person against an AI. The second case also covers a real wooden board: you type in your friend's moves and copy the AI's moves onto the board;
- click a pit or press keys 1–6; pits you cannot play are dimmed;
- South at the bottom, North at the top, and each player numbers their pits 1–6 from their own left;
- Undo in both cases: one move in a game between two people, and back to your last turn against an AI;
- a start menu to pick the agents and who moves first;
- a Hint button;
- a thoughts panel, with every checkbox off by default.

**Watch** (window):
- an AI plays an AI;
- pause, step, and a speed slider;
- a **thoughts** panel with a checkbox for each part: move scores over the pits, expected line of play, and work done (positions, depth, time).

**Tournament** (terminal):
- **random openings**, each played twice with the agents swapping sides;
- reports win / draw / loss with a 95% confidence interval, the average score difference and the time per move;
- writes a CSV and uses all CPU cores.

**Game records.**
- Moves are written a–f for South and A–F for North.
- We keep the last 100 Play and Watch games.
- A tournament is saved only with `--save`, and we keep the last 10.

**AI thinking.**
- Agents start with a fixed depth. We add a time limit (iterative deepening) later.
- Agents run in a background thread so the window stays responsive.

## Steps

- [x] 1. Engine and tests against OpenSpiel.
- [x] 2. Play for two people in Pygame, and a README with run commands.
- [x] 3. Agent interface, the Random agent, Play against AI, Undo.
- [x] 4. Tournament and game records. Random vs Random should give about 50/50.
- [x] 5. Watch with the thoughts panel.
- [ ] 6. Greedy agent, then a tournament.
- [ ] 7. Minimax with the `store_diff` heuristic, then a tournament.
- [ ] 8. Alpha-beta, then a tournament. It should give the same moves as Minimax, only faster.
- [ ] 9. Better heuristics: seeds on my side, weak pits with 1–2 seeds, mobility, a big pit with 12+ seeds.
- [ ] 10. Move ordering, iterative deepening and a time limit.
- [ ] 11. MCTS.
- [ ] 12. OpenSpiel agents (alpha-beta, MCTS) as outside opponents.

After each agent step, run a tournament against the agents we already have, to see if the new one is really stronger.

## Later

- Thoughts: the score of the current position, and a chart of that score over the game.
- Watch: step back and rewind through the game.
- A web front end, if Pygame does not feel right.
