"""Play: two people share one computer, or a person plays against an AI agent."""

import time

import pygame

from awale.agents import Agent
from awale.engine import Game, Side
from awale.ui.agent_thread import AgentThread
from awale.ui.board_view import BACKGROUND, HEIGHT, TEXT, TEXT_SOFT, WIDTH, BoardView, pit_at
from awale.ui.widgets import Button, blit_centered

PIT_KEYS = {
    **{getattr(pygame, f"K_{n}"): n for n in range(1, 7)},
    **{getattr(pygame, f"K_KP{n}"): n for n in range(1, 7)},
}
HELP = "Click a pit or press 1-6 (from your own left).    Esc: quit"
# An AI's move waits at least this long (seconds), so you can see your own move land first.
AI_MOVE_DELAY = 0.7


class PlayScreen:
    """One Play game: turns clicks and key presses into moves, lets AI agents move, and draws the window."""

    def __init__(
        self,
        players: dict[Side, Agent | None] | None = None,
        first: Side = Side.SOUTH,
        ai_move_delay: float = AI_MOVE_DELAY,
    ):
        # The AI agent for each side, or None where a person clicks the pits.
        self.players = players or {Side.SOUTH: None, Side.NORTH: None}
        self.first = first
        self.ai_move_delay = ai_move_delay
        self.view = BoardView()
        self.hover: tuple[int, int] | None = None
        width, gap, top = 170, 20, HEIGHT - 70
        left = (WIDTH - 3 * width - 2 * gap) // 2
        self.undo_button, self.new_game_button, self.menu_button = (
            Button(pygame.Rect(left + i * (width + gap), top, width, 44), label)
            for i, label in enumerate(["Undo (U)", "New game (N)", "Menu (M)"])
        )
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

    def handle(self, event: pygame.event.Event):
        """React to one event. Returns the screen to show next: this one, or the start menu."""
        if event.type == pygame.MOUSEMOTION:
            self.hover = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = pit_at(event.pos)
            if clicked and clicked[0] is self.game.position.to_move:
                self.try_move(clicked[1])
            elif self.undo_button.contains(event.pos):
                self.undo()
            elif self.new_game_button.contains(event.pos):
                self.new_game()
            elif self.menu_button.contains(event.pos):
                return self.open_menu()
        elif event.type == pygame.KEYDOWN:
            if event.key in PIT_KEYS:
                self.try_move(PIT_KEYS[event.key])
            elif event.key in (pygame.K_u, pygame.K_BACKSPACE):
                self.undo()
            elif event.key == pygame.K_n:
                self.new_game()
            elif event.key == pygame.K_m:
                return self.open_menu()
        return self

    def update(self) -> None:
        """Called every frame. Starts an AI thinking when it is its turn, and plays its move when it is ready."""
        if self.game.is_over or self.agent_to_move is None:
            return
        if self.thinking is None:
            self.thinking = AgentThread(self.agent_to_move, self.game.position)
            return
        waited = time.monotonic() - self.thinking.started
        if not self.thinking.is_done or waited < self.ai_move_delay:
            return
        thinking, self.thinking = self.thinking, None
        if thinking.error:
            raise thinking.error
        self._play(thinking.move)

    def try_move(self, pit: int) -> None:
        """Play `pit` for the person to move. Does nothing if that move is not allowed."""
        if pit in self.playable:
            self._play(pit)

    def _play(self, pit: int) -> None:
        mover = self.game.position.to_move
        store_before = self.game.position.store(mover)
        self.game.play(pit)
        self.message = f"{self.player_name(mover)} played pit {pit}"
        # When the game ends, the stores also get the seeds left in each row, so that is not a capture.
        captured = self.game.position.store(mover) - store_before
        if captured and not self.game.is_over:
            self.message += f" and captured {captured} seeds"
        self.message += "."

    def undo(self) -> None:
        """Take back moves until a person is to move: one move between two people,
        or back to your last turn against an AI."""
        target = self._undo_target()
        if target is None:
            return
        while len(self.game.moves) > target:
            self.game.undo()
        self.thinking = None  # if an AI was thinking, its move is no longer wanted
        self.message = ""

    def _undo_target(self) -> int | None:
        """How many moves to keep after an undo, or None if there is nothing to undo."""
        people = {side for side, agent in self.players.items() if agent is None}
        positions = self.game.positions
        for moves in range(len(self.game.moves) - 1, -1, -1):
            if positions[moves].to_move in people:
                return moves
        return None

    def open_menu(self):
        from awale.ui.menu import PERSON, MenuScreen  # imported here because the menu imports this file

        choices = {side: agent.name if agent else PERSON for side, agent in self.players.items()}
        return MenuScreen(choices, self.first)

    def player_name(self, side: Side) -> str:
        agent = self.players[side]
        return f"{side.name.title()} ({agent.name})" if agent else side.name.title()

    @property
    def wants_hand_cursor(self) -> bool:
        if not self.hover:
            return False
        over_pit = pit_at(self.hover)
        if over_pit and over_pit[0] is self.game.position.to_move and over_pit[1] in self.playable:
            return True
        return self.menu_button.contains(self.hover) or self.new_game_button.contains(self.hover) or (
            self.undo_button.contains(self.hover) and self._undo_target() is not None
        )

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

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        last_move = None
        if self.game.moves:
            # The player who moved last is the one not to move now.
            last_move = (self.game.position.to_move.opponent, self.game.moves[-1])
        hover_pit = pit_at(self.hover) if self.hover else None
        self.view.draw(surface, self.game.position, self.playable, hover_pit, last_move)
        blit_centered(surface, self.view.font_big, self.status(), TEXT, (WIDTH // 2, 35))
        blit_centered(surface, self.view.font_small, self.message, TEXT_SOFT, (WIDTH // 2, 68))
        blit_centered(surface, self.view.font_small, HELP, TEXT_SOFT, (WIDTH // 2, HEIGHT - 100))
        self.undo_button.draw(surface, self.view.font_small, self.hover, enabled=self._undo_target() is not None)
        self.new_game_button.draw(surface, self.view.font_small, self.hover)
        self.menu_button.draw(surface, self.view.font_small, self.hover)
