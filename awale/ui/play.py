"""Play: two people share one computer, or a person plays against an AI agent."""

import pygame

from awale.agents import Agent
from awale.engine import Side
from awale.ui.board_view import HEIGHT, TEXT_SOFT, WIDTH, pit_at
from awale.ui.game_screen import GameScreen
from awale.ui.widgets import Button, blit_centered

PIT_KEYS = {
    **{getattr(pygame, f"K_{n}"): n for n in range(1, 7)},
    **{getattr(pygame, f"K_KP{n}"): n for n in range(1, 7)},
}
HELP = "Click a pit or press 1-6 (from your own left).    Esc: quit"
# An AI's move waits at least this long (seconds), so you can see your own move land first.
AI_MOVE_DELAY = 0.7


class PlayScreen(GameScreen):
    """One Play game: turns clicks and key presses into moves, lets AI agents move, and draws the window."""

    def __init__(
        self,
        players: dict[Side, Agent | None] | None = None,
        first: Side = Side.SOUTH,
        ai_move_delay: float = AI_MOVE_DELAY,
    ):
        width, gap, top = 170, 20, HEIGHT - 70
        left = (WIDTH - 3 * width - 2 * gap) // 2
        self.undo_button, self.new_game_button, self.menu_button = (
            Button(pygame.Rect(left + i * (width + gap), top, width, 44), label)
            for i, label in enumerate(["Undo (U)", "New game (N)", "Menu (M)"])
        )
        super().__init__(players or {Side.SOUTH: None, Side.NORTH: None}, first, ai_move_delay)

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

    def try_move(self, pit: int) -> None:
        """Play `pit` for the person to move. Does nothing if that move is not allowed."""
        if pit in self.playable:
            self.play(pit)

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

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_game(surface)
        blit_centered(surface, self.view.font_small, HELP, TEXT_SOFT, (WIDTH // 2, HEIGHT - 100))
        self.undo_button.draw(surface, self.view.font_small, self.hover, enabled=self._undo_target() is not None)
        self.new_game_button.draw(surface, self.view.font_small, self.hover)
        self.menu_button.draw(surface, self.view.font_small, self.hover)
