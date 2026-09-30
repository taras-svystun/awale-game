# Awalé

Awalé is a two-player board game from West Africa (the Ivory Coast name for Oware, "abapa" rules). This project lets people play it on one computer, against each other or against AI, and lets us build and compare AI players.

## Language

### The board

**Board**:
Two rows of 6 pits, one row for each player. The game starts with 4 seeds in every pit (48 seeds in total).
_Avoid_: Field, table

**Pit**:
One of the 12 holes on the board that holds seeds.
_Avoid_: Basket, house, hole, trou, cup

**Row**:
The 6 pits on one player's side. A player may only start a move from a pit in their own row. Each player numbers their pits 1 to 6 from their own left.
_Avoid_: Side, camp

**South / North**:
The two sides of the board. South sits at the bottom of the screen, North at the top.
_Avoid_: Player 1 / Player 2, white / black, top / bottom

**Seed**:
One playing piece. All seeds are the same.
_Avoid_: Ball, stone, graine, bean

**Store**:
The pile of seeds a player has captured. Seeds in a store never go back to the board.
_Avoid_: Granary, bank, mancala, grenier, score pit

### Moves

**Move**:
Choosing one non-empty pit in your own row and sowing its seeds.
_Avoid_: Turn, play

**Sow**:
Take all seeds from the chosen pit and drop them one by one into the next pits, counter-clockwise. If there are 12 or more seeds, the chosen pit is skipped when the seeds go around.
_Avoid_: Distribute, spread, deal

**Capture**:
When the last seed lands in an opponent's pit and makes it 2 or 3 seeds, the player takes those seeds to their store. Then they check the pit before it, and keep taking while the opponent's pits have 2 or 3 seeds.
_Avoid_: Take, harvest, eat

**Grand slam**:
A move that would capture every seed in the opponent's row. The move is allowed, but it captures nothing.
_Avoid_: Starving move

**Feeding**:
When the opponent's row is empty, the player must make a move that puts seeds into it. If no such move exists, the game ends and the player takes all seeds in their own row.
_Avoid_: Giving, nourishing

### End of the game

**Win**:
A player wins when their store has 25 or more seeds. If both stores end with 24, it is a draw.

**Repetition**:
When a position happens again, the game ends and each player takes the seeds left in their own row.
_Avoid_: Loop, cycle

### Who plays

**Player**:
One of the two sides (South or North) in a specific game. An agent plays for a player.
_Avoid_: Side, user

**Agent**:
Anything that chooses a move in a position: a person clicking pits, a random chooser, or an AI like "minimax, depth 4, heuristic A".
_Avoid_: Bot, AI player, engine, strategy

**Heuristic**:
A function that looks at a position and gives it a number: how good it is for one player. It does not choose moves by itself.
_Avoid_: Evaluation, strategy, score function

**Search**:
A method that looks ahead through possible moves to pick one, such as minimax, alpha-beta or MCTS. Search usually uses a heuristic to judge the positions it reaches.
_Avoid_: Strategy, algorithm

**Thoughts**:
What an agent shows about how it chose its move: the score of each possible move, the line of play it expects, and how much work it did.
_Avoid_: Brains, debug info, logs

### Ways to use the game

**Play**:
One game in a window where at least one agent is a person. Two people can share the computer, or a person plays against an AI.
_Avoid_: Match, session

**Watch**:
One game between two AI agents, shown in a window move by move, with their thoughts next to the board.
_Avoid_: Spectate, replay

**Tournament**:
Many games between AI agents, run without a window, to compare them with numbers instead of by eye.
_Avoid_: Arena, benchmark, simulation

**Hint**:
In Play, the move an AI agent would choose for the person whose turn it is, shown only when the person asks.
_Avoid_: Tip, suggestion, assist

**Game record**:
A saved game: who played South and North, the list of moves, and the result. Moves are written as a–f for South's pits and A–F for North's.
_Avoid_: Log, replay, history, save file

**Random opening**:
The first few moves of a tournament game, chosen at random so that games between the same agents are not all identical. Each random opening is played twice, with the agents swapping sides.
_Avoid_: Warm-up, seed moves
