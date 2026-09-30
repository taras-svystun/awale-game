"""Run an AI agent in a background thread, so the window keeps drawing while it thinks."""

import threading
import time

from awale.agents import Agent
from awale.engine import Position


class AgentThread:
    """One agent choosing one move. Python cannot stop a thread, so to cancel, just forget this object."""

    def __init__(self, agent: Agent, position: Position):
        self.position = position
        self.started = time.monotonic()
        self.move: int | None = None
        self.error: Exception | None = None
        self._agent = agent
        # daemon=True: closing the window does not wait for an agent that is still thinking.
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self.move = self._agent.choose_move(self.position)
        except Exception as error:
            # Keep it for the main thread to raise, so a broken agent stops the program
            # instead of leaving the window waiting for a move forever.
            self.error = error

    @property
    def is_done(self) -> bool:
        return not self._thread.is_alive()

    def wait(self) -> None:
        self._thread.join()
