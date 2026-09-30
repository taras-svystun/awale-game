"""What Play and Watch share: one game, the agents in it, and an AI agent thinking in the background."""

import time

import pygame

from awale.agents import Agent
from awale.engine import Game, Position, Side
from awale.records import GameRecord, save_game
from awale.ui.agent_thread import AgentThread
from awale.ui.board_view import BACKGROUND, TEXT, TEXT_SOFT, WIDTH, BoardView, pit_at
from awale.ui.widgets import blit_centered

# How a person is named in the menu and in game records.
PERSON = "Person"


class GameScreen:
    """One game on the screen. PlayScreen and WatchScreen add their own buttons and keys."""

    def __init__(self, players: dict[Side, Agent | None], first: Side, move_delay: float):
        # The AI agent for each side, or None where a person clicks the pits.
        self.players = players
        self.first = first
        # An AI's move waits at least this long (seconds), so people can follow the game.
        self.move_delay = move_delay
        self.view = BoardView()
        self.hover: tuple[int, int] | None = None
        self.new_game()

    def new_game(self) -> None:
        self.game = Game(first=self.first)
        self.message = ""
        self.thinking: AgentThread | None = None  # the AI agent choosing a move right now

    @property
    def agent_to_move(self) -> Agent | None:
        return self.players[self.game.position.to_move]

    @property
    def playable(self) -> list[int]:
        """Pits a person may click now. None while an AI is to move."""
        if self.game.is_over or self.agent_to_move:
            return []
        return self.game.position.legal_moves()

    def update(self) -> None:
        """Called every frame. Starts an AI thinking when it is its turn, and plays its move when it is ready."""
        if self.game.is_over or self.agent_to_move is None:
            return
        if self.thinking is None:
            self.thinking = AgentThread(self.agent_to_move, self.game.position)
            return
        if not self.thinking.is_done:
            return
        if self.thinking.error:
            raise self.thinking.error
        if self.ready_to_play(self.thinking):
            thinking, self.thinking = self.thinking, None
            self.play(thinking.thoughts.move)

    def ready_to_play(self, thinking: AgentThread) -> bool:
        """The AI has chosen its move. Is it time to play it? Play and Watch wait in different ways."""
        return time.monotonic() - thinking.started >= self.move_delay

    def play(self, pit: int) -> None:
        mover = self.game.position.to_move
        store_before = self.game.position.store(mover)
        self.game.play(pit)
        self.message = f"{self.player_name(mover)} played pit {pit}"
        # When the game ends, the stores also get the seeds left in each row, so that is not a capture.
        captured = self.game.position.store(mover) - store_before
        if captured and not self.game.is_over:
            self.message += f" and captured {captured} seeds"
        self.message += "."
        if self.game.is_over:
            self.save_record()

    def save_record(self) -> None:
        """Save the finished game in records/games. If you undo and finish it again, that is saved too."""
        if self.game.positions[0] != Position.start(self.first):
            return  # a game set up by hand (the tests do this) cannot be told by its moves alone
        save_game(GameRecord.of(self.game, self.agent_name(Side.SOUTH), self.agent_name(Side.NORTH)))

    def open_menu(self):
        from awale.ui.menu import MenuScreen  # imported here because the menu imports this file

        choices = {side: self.agent_name(side) for side in Side}
        return MenuScreen(choices, self.first)

    def agent_name(self, side: Side) -> str:
        agent = self.players[side]
        return agent.name if agent else PERSON

    def player_name(self, side: Side) -> str:
        agent = self.players[side]
        return f"{side.name.title()} ({agent.name})" if agent else side.name.title()

    def status(self) -> str:
        result = self.game.result
        if result is None:
            to_move = self.player_name(self.game.position.to_move)
            return f"{to_move} is thinking..." if self.agent_to_move else f"{to_move} to move"
        south, north = result.score
        if result.winner is None:
            return f"Draw, {south} to {north}"
        high, low = max(south, north), min(south, north)
        return f"{self.player_name(result.winner)} wins, {high} to {low}"

    def draw_game(self, surface: pygame.Surface, lit: list[int] | None = None) -> None:
        """Draw the background, the status line, the last move's message and the board.

        `lit` are the pits drawn bright. By default they are the pits a person may click.
        """
        surface.fill(BACKGROUND)
        last_move = None
        if self.game.moves:
            # The player who moved last is the one not to move now.
            last_move = (self.game.position.to_move.opponent, self.game.moves[-1])
        # A hover ring only where a click would play.
        hover_pit = pit_at(self.hover) if self.hover and self.playable else None
        self.view.draw(surface, self.game.position, self.playable if lit is None else lit, hover_pit, last_move)
        blit_centered(surface, self.view.font_big, self.status(), TEXT, (WIDTH // 2, 35))
        blit_centered(surface, self.view.font_small, self.message, TEXT_SOFT, (WIDTH // 2, 68))
