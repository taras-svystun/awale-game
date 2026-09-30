"""The Greedy agent: looks one move ahead and takes the biggest capture."""

from awale.agents.base import Agent, Thoughts
from awale.engine import Position


class GreedyAgent(Agent):
    """Plays the move that captures the most seeds right now. Never thinks about the answer."""

    name = "Greedy"

    def think(self, position: Position) -> Thoughts:
        me = position.to_move
        # Try every legal move once, and count the seeds it puts in our store.
        # The engine applies all the rules, so a grand slam counts as 0 here, as it should.
        scores = {pit: position.play(pit).store(me) - position.store(me) for pit in position.legal_moves()}
        best = max(scores.values())
        # When several moves capture the same (often 0), Greedy has no reason to prefer one,
        # so it picks at random instead of always the leftmost pit.
        move = self.rng.choice([pit for pit, score in scores.items() if score == best])
        return Thoughts(move, scores, line=(move,), positions=len(scores), depth=1)
