"""OpenSpiel's agents: its MCTS and its alpha-beta, as opponents written by someone else.

OpenSpiel (from DeepMind) has its own Awalé, the game "oware", with the same rules as ours
(see docs/adr/0001). These agents give the game to OpenSpiel's search in OpenSpiel's own form,
and play the move it chooses. So we can test our agents against code we did not write.
"""

from collections.abc import Callable

import pyspiel
from open_spiel.python.algorithms import minimax

from awale.agents.base import Agent, Thoughts
from awale.agents.heuristics import store_diff
from awale.agents.minimax_agent import WIN
from awale.engine import Game, Position, Side

OWARE = pyspiel.load_game("oware")

# Seconds per move when neither a number of playouts nor a time is given. The same as our MCTS.
TIME_LIMIT = 0.1
# How much OpenSpiel's MCTS tries the moves it tried less. 2 is the value in OpenSpiel's own examples.
# Its results go from -1 (a loss) to 1 (a win), twice as wide as ours from 0 to 1, so this is C = 1 for our MCTS:
# a little less trying than our √2.
UCT_C = 2.0
# OpenSpiel's MCTS wants a number of playouts. With only a time limit, we give it one it never reaches.
NO_PLAYOUT_LIMIT = 10**9
# Memory for OpenSpiel's MCTS tree. In 1 second it grows to a few megabytes.
MEMORY_MB = 1000
DEPTH = 6  # the same as our AlphaBeta


def openspiel_state(game: Game) -> pyspiel.State:
    """OpenSpiel's state for the position on the board in `game`.

    OpenSpiel cannot start from any position, only from the start, so we play all the moves of the game again in it.
    That also tells OpenSpiel's search the earlier positions, so it sees when a repetition would end the game.
    OpenSpiel's player 0 always moves first: South when South moved first, North when North did.
    A move means the same in both: OpenSpiel's action k is the mover's pit k + 1, counted from their own left.
    """
    start = game.positions[0]
    if start != Position.start(start.to_move):
        raise ValueError("OpenSpiel's agents can only play a game that begins at the start position")
    state = OWARE.new_initial_state()
    for pit in game.moves:
        state.apply_action(pit - 1)
    return state


def position_of(state: pyspiel.State) -> Position:
    """Our Position for an OpenSpiel state that is not over, with OpenSpiel's player 0 as South.

    When North moved first, this is the real board turned around. A heuristic does not mind: it looks at
    "my" pits and "the opponent's", never at which of them is South.
    """
    # OpenSpiel's text looks like "0 | 3 5 | 1 6 5 ..." (player to move | stores | player 0's 6 pits, then player 1's).
    _player, stores, board = state.observation_string(0).split(" | ")
    south, north = map(int, stores.split())
    return Position(tuple(map(int, board.split())), (south, north), Side(state.current_player()))


class OpenSpielAgent(Agent):
    """What both OpenSpiel agents share: they think about a whole game, not only about a position."""

    def think(self, position: Position) -> Thoughts:
        # A position with no moves before it. OpenSpiel can only take it if it is the start position.
        return self.think_in_game(Game(start=position))

    def think_in_game(self, game: Game) -> Thoughts:
        return self.search(openspiel_state(game))

    def search(self, state: pyspiel.State) -> Thoughts:
        """Choose a move in OpenSpiel's state. Each OpenSpiel agent writes its own."""
        raise NotImplementedError


class OpenSpielMCTSAgent(OpenSpielAgent):
    """OpenSpiel's MCTS, written in C++: the same idea as our MCTS (see docs/agents/mcts.md), but about 7 times faster.

    It is set up like OpenSpiel's own examples: one random playout per new node, C = 2, and the MCTS-Solver,
    which marks a position as surely won or lost when the tree reaches the end of the game from it.
    """

    name = "OpenSpielMCTS"

    def __init__(self, seed: int | None = None, playouts: int | None = None, time_limit: float | None = None):
        super().__init__(seed)
        if playouts is None and time_limit is None:
            time_limit = TIME_LIMIT
        if playouts is not None and playouts < 1:
            raise ValueError(f"{self.name} needs at least 1 playout, not {playouts}")
        if time_limit is not None and time_limit <= 0:
            raise ValueError(f"{self.name} needs a time limit above 0 seconds, not {time_limit}")
        self.playouts = playouts  # playouts per move, or None: only the time limit stops it
        self.time_limit = time_limit  # seconds per move, or None for no time limit

    def search(self, state: pyspiel.State) -> Thoughts:
        # A new seed from our own random generator for each move, so the same seed always gives the same game.
        seed = self.rng.getrandbits(31)
        bot = pyspiel.MCTSBot(
            OWARE,
            pyspiel.RandomRolloutEvaluator(1, seed),  # 1 random playout to judge each new node
            UCT_C,
            self.playouts or NO_PLAYOUT_LIMIT,
            MEMORY_MB,
            True,  # solve: use the MCTS-Solver
            seed,
            False,  # verbose
            pyspiel.ChildSelectionPolicy.UCT,
            self.time_limit or -1,  # -1 means no time limit
        )
        root = bot.mcts_search(state)
        if not root.children:
            # OpenSpiel's first playout starts at the top, before it adds any move to the tree.
            # With only that one (1 playout, or almost no time), it knows nothing about the moves yet.
            return Thoughts(self.rng.choice(state.legal_actions()) + 1, playouts=root.explore_count)
        # OpenSpiel's choice: a surely won move first, then the move tried most, then the best result.
        best = root.best_child()
        # OpenSpiel adds a child for every legal move at once, so a move may have no playouts yet.
        scores = {child.action + 1: win_share(child) for child in root.children if child.explore_count}
        tree = list(walk(root, 0))
        return Thoughts(
            move=best.action + 1,
            scores=dict(sorted(scores.items())),
            line=expected_line(best),
            # The positions in its tree. Ours also counts the positions in its playouts, but OpenSpiel does not say.
            positions=len(tree) - 1,
            depth=max(depth for depth, _ in tree),
            playouts=root.explore_count,
        )


def win_share(node: pyspiel.SearchNode) -> float:
    """The share of points the player who moved into `node` got, from 0 to 1, like our MCTS's scores.

    OpenSpiel counts results from -1 (a loss) to 1 (a win). A node the solver proved has an exact outcome.
    """
    if node.outcome:
        return (node.outcome[node.player] + 1) / 2
    return (node.total_reward / node.explore_count + 1) / 2


def walk(node: pyspiel.SearchNode, depth: int):
    """`node` and every node below it that had a playout, with how many moves below the top each one is."""
    yield depth, node
    for child in node.children:
        if child.explore_count:
            yield from walk(child, depth + 1)


def expected_line(node: pyspiel.SearchNode) -> tuple[int, ...]:
    """`node`'s move, then OpenSpiel's best answer, and so on, while the answer was tried more than once.

    The same rule as our MCTS's line: a move tried once has seen only one random game.
    """
    line = [node.action + 1]
    while node.children:
        node = node.best_child()
        if node.explore_count < 2:
            break
        line.append(node.action + 1)
    return tuple(line)


class OpenSpielAlphaBetaAgent(OpenSpielAgent):
    """OpenSpiel's alpha-beta, written in Python, with one of our heuristics where it stops looking.

    OpenSpiel has no heuristic for Awalé: its alpha-beta is general and works for any game.
    It wants values from -1 (a loss) to 1 (a win), so we divide the heuristic by WIN, which no heuristic reaches.
    """

    name = "OpenSpielAlphaBeta"

    def __init__(
        self,
        seed: int | None = None,
        depth: int = DEPTH,
        heuristic: Callable[[Position, Side], float] = store_diff,
    ):
        super().__init__(seed)
        if depth < 1:
            raise ValueError(f"{self.name} needs a depth of at least 1, not {depth}")
        self.depth = depth
        self.heuristic = heuristic
        self.positions = 0  # counted by the heuristic, and reset for each move

    def search(self, state: pyspiel.State) -> Thoughts:
        me = state.current_player()
        self.positions = 0

        def value(state: pyspiel.State) -> float:
            # OpenSpiel's alpha-beta calls this where it stops looking. The value is for `me`, whoever is to move.
            self.positions += 1
            return self.heuristic(position_of(state), Side(me)) / WIN

        # OpenSpiel's alpha-beta gives only its best move and its value. To get a score for every move,
        # like our AlphaBeta, we ask it about the position after each move, one move less deep.
        scores, answers = {}, {}
        for action in state.legal_actions():
            score, answer = minimax.alpha_beta_search(
                OWARE, state.child(action), value, self.depth - 1, maximizing_player_id=me
            )
            # Back to seeds, like our agents' scores: a win is WIN. Rounded, since 0.3 / 100 * 100 is not exactly 0.3.
            scores[action + 1] = round(score * WIN, 6)
            answers[action + 1] = answer
        # The first move with the best score, as OpenSpiel's alpha-beta would choose from the top.
        move = max(scores, key=scores.get)
        # It returns None for its answer where the search stops, and the line ends there.
        line = (move,) if answers[move] is None else (move, answers[move] + 1)
        return Thoughts(move, scores, line, self.positions, self.depth)
