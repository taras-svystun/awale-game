# Awalé

A local Awalé game in Python (Pygame) for playing people and AI agents, and a lab for writing and comparing AI agents.

- `CONTEXT.md`: the glossary. Use its terms in code, docs and commit messages.
- `docs/PLAN.md`: the roadmap and what we agreed. Read it when starting a step.
- `docs/adr/`: decisions and their reasons. Read before changing the rules, the engine or a tech choice.
- `docs/journal.md`: plain-English history of every finished step.

## Working with Taras

Taras knows Python well and is new to AI-assisted coding. Reply to him in Ukrainian. Write everything in the repo (code, comments, docs, commits) in plain, simple English, so it reads like he wrote it.

AI agents are a shared lesson. For Random, Greedy and Minimax, Taras writes the algorithm: I prepare the skeleton, tests and Tournament wiring, then give hints and review. From Alpha-beta on, I write the first version with explanations and Taras experiments with it.

## Finishing a step

A step is one item in `docs/PLAN.md`, or a smaller piece agreed in chat. It is done when all of these are true:

1. Tests pass: `.venv/bin/pytest`.
2. `README.md` has a copy-paste command for every way to run the project. Taras should never guess a command.
3. `docs/journal.md` has a new entry: what we did, why, and how, in a few short lines.
4. The step is ticked in `docs/PLAN.md`.
5. The work is committed. Subject: imperative, under 72 characters. Body: why the change exists, so a reader a year later understands the reason. One commit per logical change.
6. The commits are pushed to `origin`.
7. My reply to Taras has a short summary (what, why, how) and a "check it yourself" list: exact commands to run and things to click.
