# OpenSpiel's agents replay the whole game

OpenSpiel's agents (step 12) search in OpenSpiel's own `oware` state. In the Python bindings, that state can only start at the start position: there is no way to set up a board by hand. So an OpenSpiel agent cannot think about a lone `Position`. It needs every move from the start, and plays them all again in OpenSpiel. We added `Agent.think_in_game(game)`, which Tournament, Play and Watch now call instead of `think(position)`. By default it just calls `think(game.position)`, so our own agents did not change. The window gives the agent a copy of the game, since it may undo while the agent thinks in its thread. OpenSpiel's agents cannot play a game that was set up by hand (only the tests do that).

OpenSpiel is now a normal dependency, not only for the tests: the agents need it to run.

## Considered Options

- **OpenSpiel's search on our engine**: wrap our `Position` in a small class with the methods OpenSpiel's Python algorithms call. It works from any position, but uses our rules instead of OpenSpiel's, and only the Python algorithms accept it. OpenSpiel's MCTS in C++, about 7 times faster than ours, needs a real OpenSpiel state.
- **Guess the moves from the position**: look for the moves that lead from the last position the agent saw, or from the start, to this one. The tournament's random openings make it too slow: there are 135 000 different positions after 7 moves.
- **A Position that knows its earlier moves**: it would change what a Position is (see `CONTEXT.md`) for every agent, to help two.
