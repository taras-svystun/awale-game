"""The MCTS agent: Monte Carlo tree search. It judges moves by playing many random games to the end."""

import math
import time

from awale.agents.base import Agent, Thoughts
from awale.engine import WINNING_STORE, Position, Side

# Seconds per move when neither a number of playouts nor a time is given. The same as Deepening, to compare them.
TIME_LIMIT = 0.1
# How much to try the moves that were tried less. The square root of 2 is the textbook value for results from 0 to 1.
EXPLORATION = math.sqrt(2)
# A random game from the start lasts about 110 moves, but a few go round in circles for ever.
# A playout that gets this long is stopped and judged as if the game ended there.
PLAYOUT_MOVES = 200


class Node:
    """One position in the tree that MCTS grows, and what the playouts through it gave."""

    __slots__ = ("position", "move", "parent", "children", "untried", "visits", "wins")

    def __init__(self, position: Position, move: int | None = None, parent: "Node | None" = None):
        self.position = position
        self.move = move  # the pit played in the parent's position to get here
        self.parent = parent
        self.children: list[Node] = []
        # Legal moves that have no child yet. Empty when the game ends here.
        self.untried = [] if position.ends_game() else position.legal_moves()
        self.visits = 0  # how many playouts went through here
        # Their points for the player who played `move`: 1 for each win, 1/2 for each draw, 0 for each loss.
        self.wins = 0.0

    @property
    def win_share(self) -> float:
        """The share of points the player who played `move` got in the playouts through here: from 0 to 1."""
        return self.wins / self.visits


class MCTSAgent(Agent):
    """Grows a tree of positions, one playout at a time. Each playout has four steps:

    1. Selection: from the top, go down the tree, each time to the move that looks best,
       with a bonus for moves that were tried only a few times.
    2. Expansion: at the first position with a move that was never tried, try it and add the new position to the tree.
    3. Playout: from there, play random moves until the game ends.
    4. Backpropagation: every position on the way down learns who won.

    Good moves get tried more and more, so their part of the tree grows deeper.
    When the playouts or the time run out, it plays the move it tried most.
    It needs no heuristic: the random games to the end judge the positions instead.
    """

    name = "MCTS"

    def __init__(
        self,
        seed: int | None = None,
        playouts: int | None = None,
        time_limit: float | None = None,
        exploration: float = EXPLORATION,
    ):
        super().__init__(seed)
        if playouts is None and time_limit is None:
            time_limit = TIME_LIMIT
        if playouts is not None and playouts < 1:
            raise ValueError(f"{self.name} needs at least 1 playout, not {playouts}")
        if time_limit is not None and time_limit <= 0:
            raise ValueError(f"{self.name} needs a time limit above 0 seconds, not {time_limit}")
        self.playouts = playouts  # playouts per move, or None: only the time limit stops it
        self.time_limit = time_limit  # seconds per move, or None for no time limit
        self.exploration = exploration
        self.positions = 0  # counted while it thinks, and reset for each move

    def think(self, position: Position) -> Thoughts:
        root = self.grow_tree(position)
        # The move tried most, not the one with the best share of wins: a move tried 3 times and won 3 times
        # may just have been lucky. On a tie, the better share of wins, then a random choice.
        most = max((child.visits, child.win_share) for child in root.children)
        move = self.rng.choice(sorted(c.move for c in root.children if (c.visits, c.win_share) == most))
        scores = {child.move: child.win_share for child in sorted(root.children, key=lambda child: child.move)}
        deepest = max(depth for depth, _ in self.walk(root))
        return Thoughts(move, scores, self.expected_line(root, move), self.positions, deepest, playouts=root.visits)

    def grow_tree(self, position: Position) -> Node:
        """Run playouts from `position` until the playouts or the time run out. Returns the top of the tree.

        Every legal move is tried at least once, even when the time is up, so every move gets a score.
        """
        started = time.perf_counter()
        self.positions = 0
        root = Node(position)
        while root.untried or not self.is_done(root.visits, started):
            # 1. Selection. Stop at a position with a move never tried, or where the game ends.
            node = root
            while not node.untried and node.children:
                node = self.select(node)
            # 2. Expansion. Try one of the moves never tried, chosen at random.
            if node.untried:
                move = node.untried.pop(self.rng.randrange(len(node.untried)))
                child = Node(node.position.play(move), move, node)
                node.children.append(child)
                node = child
                self.positions += 1
            # 3. Playout.
            end = self.playout(node.position)
            # 4. Backpropagation. Each node counts the points of the player who moved into it,
            # because that is the player who chooses it in the selection step.
            while node.parent is not None:
                node.visits += 1
                node.wins += points(end, node.parent.position.to_move)
                node = node.parent
            root.visits += 1
        return root

    def is_done(self, playouts: int, started: float) -> bool:
        """True when it has played its number of playouts, or its time is up, whichever comes first."""
        if self.playouts is not None and playouts >= self.playouts:
            return True
        return self.time_limit is not None and time.perf_counter() - started >= self.time_limit

    def select(self, node: Node) -> Node:
        """The child with the highest UCB score: its share of wins, plus a bonus for being tried few times.

        The bonus grows slowly as the parent is visited more, and shrinks fast as the child itself is visited more.
        So a move that looks bad is still tried now and then, in case the first playouts were unlucky.
        """
        log_visits = math.log(node.visits)
        return max(
            node.children,
            key=lambda child: child.win_share + self.exploration * math.sqrt(log_visits / child.visits),
        )

    def playout(self, position: Position) -> Position:
        """Play random moves until the game ends, or for PLAYOUT_MOVES moves at most.

        Returns the last position, with the seeds left on the board collected by the owner of each row.
        """
        for _ in range(PLAYOUT_MOVES):
            # The same check as position.ends_game(), but it asks for the legal moves only once per move.
            # Playouts are almost all of MCTS's work, and this makes them about a quarter faster.
            moves = position.legal_moves()
            if not moves or max(position.stores) >= WINNING_STORE:
                break
            position = position.play(self.rng.choice(moves))
            self.positions += 1
        return position.with_rows_collected()

    @staticmethod
    def walk(node: Node, depth: int = 0):
        """Every node in the tree below `node`, with how many moves below it the node is."""
        yield depth, node
        for child in node.children:
            yield from MCTSAgent.walk(child, depth + 1)

    @staticmethod
    def expected_line(root: Node, move: int) -> tuple[int, ...]:
        """`move`, then the answer tried most after it, and so on, while the answer was tried more than once.

        A move tried only once has seen a single random game, so it says nothing about what the players expect.
        """
        node = next(child for child in root.children if child.move == move)
        line = [move]
        while node.children:
            node = max(node.children, key=lambda child: child.visits)
            if node.visits < 2:
                break
            line.append(node.move)
        return tuple(line)


def points(end: Position, side: Side) -> float:
    """1 if `side` won the game that ended in `end`, 1/2 for a draw, 0 for a loss."""
    mine, theirs = end.store(side), end.store(side.opponent)
    return 1.0 if mine > theirs else 0.5 if mine == theirs else 0.0
