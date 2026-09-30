# Own Python game engine, OpenSpiel only as a reference

We write the Awalé rules ourselves in plain Python (about 150 lines) instead of using OpenSpiel's `oware` game as the engine. OpenSpiel's rules are written in C++, so we could not easily read, debug or change them, and the whole point of this project is to understand the game and the AI code. We still use OpenSpiel in two ways: as a test oracle (our engine must give the same results as OpenSpiel on thousands of random games) and as a strong opponent in tournaments. Our rules match OpenSpiel's on purpose: a grand slam captures nothing, and a repeated position ends the game.

## Considered Options

- **OpenSpiel as the engine**: well tested and fast, but the rules are a black box in C++.
- **pyAwale**: pure Python, but old, GPL, and hosted on Launchpad with little activity.
- **`mancala` on PyPI**: a different game (Kalah), not Awalé.
