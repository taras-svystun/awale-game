# Journal

A short, plain-English history of each finished step: what we did, why, and how. Newest at the bottom.

## Step 0: research and planning (2026-09-30)

**What:** We looked at the rules of Awalé and at existing code. We wrote the glossary (`CONTEXT.md`), the plan (`docs/PLAN.md`) and the first decision record (`docs/adr/0001`).

**Why:** We wanted to agree on the rules and on the words we use before writing any code, so the code, the docs and our conversations all mean the same thing.

**How:** We checked Wikipedia, French rule sheets, OpenSpiel, pyAwale and the `mancala` package on PyPI. There is no good Python Awalé with a UI or AI we could reuse. OpenSpiel has correct rules but they are written in C++, so we write our own engine in Python and use OpenSpiel to check it.
