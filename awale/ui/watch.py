"""Watch: two AI agents play each other, move by move, with their thoughts next to the board."""

import math
import time

import pygame

from awale.agents import Agent
from awale.engine import Side
from awale.ui.agent_thread import AgentThread
from awale.ui.board_view import HEIGHT, TEXT, TEXT_SOFT, WIDTH
from awale.ui.game_screen import GameScreen
from awale.ui.thoughts_view import ThoughtsPanel
from awale.ui.widgets import Button, Slider

# The speed slider goes from SLOWEST seconds per move at its left end to FASTEST at its right end.
# The window draws 30 frames a second and a move takes two frames, so faster than 0.1 s would not be true.
SLOWEST, FASTEST = 3.0, 0.1
DEFAULT_DELAY = 0.7
CONTROLS_Y = 470


def delay_at(value: float) -> float:
    """Seconds per move for a slider value from 0 to 1.

    Each step along the slider multiplies the speed by the same amount (like a volume knob),
    so going from 3 s to 1.5 s takes as much of the slider as going from 0.2 s to 0.1 s.
    """
    return SLOWEST * (FASTEST / SLOWEST) ** value


def value_for(delay: float) -> float:
    """The opposite of `delay_at`: where the slider sits for `delay` seconds per move."""
    delay = min(SLOWEST, max(FASTEST, delay))
    return math.log(delay / SLOWEST) / math.log(FASTEST / SLOWEST)


class WatchScreen(GameScreen):
    """One Watch game. It shows each agent's thoughts on the position before it plays its move."""

    def __init__(self, players: dict[Side, Agent], first: Side = Side.SOUTH, delay: float = DEFAULT_DELAY):
        if None in players.values():
            raise ValueError("Watch needs an AI agent on both sides. A game with a person is Play.")
        self.paused = False
        self.step_asked = False  # play the next move as soon as it is chosen, even while paused
        self.pause_button = Button(pygame.Rect(60, CONTROLS_Y - 22, 170, 44), "Pause (Space)")
        self.step_button = Button(pygame.Rect(245, CONTROLS_Y - 22, 130, 44), "Step (S)")
        self.speed = Slider(pygame.Rect(480, CONTROLS_Y - 3, 280, 6), value_for(delay))
        self.thoughts = ThoughtsPanel(top=505)
        width, gap, top = 170, 20, HEIGHT - 70
        left = (WIDTH - 2 * width - gap) // 2
        self.new_game_button, self.menu_button = (
            Button(pygame.Rect(left + i * (width + gap), top, width, 44), label)
            for i, label in enumerate(["New game (N)", "Menu (M)"])
        )
        super().__init__(players, first, delay)

    def new_game(self) -> None:
        super().new_game()
        self.step_asked = False

    def handle(self, event: pygame.event.Event):
        """React to one event. Returns the screen to show next: this one, or the start menu."""
        speed_before = self.speed.value
        self.speed.handle(event)
        if self.speed.value != speed_before:
            self.move_delay = delay_at(self.speed.value)
        if event.type == pygame.MOUSEMOTION:
            self.hover = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.thoughts.handle_click(event.pos)
            if self.pause_button.contains(event.pos):
                self.toggle_pause()
            elif self.step_button.contains(event.pos):
                self.step()
            elif self.new_game_button.contains(event.pos):
                self.new_game()
            elif self.menu_button.contains(event.pos):
                return self.open_menu()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_p):
                self.toggle_pause()
            elif event.key in (pygame.K_s, pygame.K_RIGHT):
                self.step()
            elif event.key == pygame.K_n:
                self.new_game()
            elif event.key == pygame.K_m:
                return self.open_menu()
        return self

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.step_asked = False

    def step(self) -> None:
        """Pause, and play just the next move."""
        self.paused = True
        self.step_asked = True

    def ready_to_play(self, thinking: AgentThread) -> bool:
        if self.step_asked:
            return True
        if self.paused:
            return False
        # Counted from when the agent finished, not from when it started, so its thoughts
        # stay on the screen for the same time however long it took to think.
        return time.monotonic() - thinking.finished >= self.move_delay

    def play(self, pit: int) -> None:
        super().play(pit)
        self.step_asked = False

    def status(self) -> str:
        if self.game.is_over:
            return super().status()
        player = self.player_name(self.game.position.to_move)
        if self.thinking and self.thinking.is_done:
            text = f"{player} chose pit {self.thinking.thoughts.move}"
        else:
            text = f"{player} is thinking..."
        return f"Paused. {text}" if self.paused else text

    @property
    def wants_hand_cursor(self) -> bool:
        if not self.hover:
            return False
        buttons = [self.pause_button, self.step_button, self.new_game_button, self.menu_button]
        return any(item.contains(self.hover) for item in [*buttons, *self.thoughts.checkboxes, self.speed])

    def draw(self, surface: pygame.Surface) -> None:
        # Nobody clicks the pits in Watch, but the ones the agent may play are still drawn bright.
        self.draw_game(surface, lit=[] if self.game.is_over else self.game.position.legal_moves())
        font = self.view.font_small
        self.pause_button.label = "Resume (Space)" if self.paused else "Pause (Space)"
        self.pause_button.draw(surface, font, self.hover, selected=self.paused)
        self.step_button.draw(surface, font, self.hover)
        label = font.render("Speed", True, TEXT_SOFT)
        surface.blit(label, label.get_rect(midright=(self.speed.rect.left - 20, CONTROLS_Y)))
        self.speed.draw(surface, self.hover)
        per_move = font.render(f"{self.move_delay:.2g} s per move", True, TEXT)
        surface.blit(per_move, per_move.get_rect(midleft=(self.speed.rect.right + 20, CONTROLS_Y)))
        mover = self.game.position.to_move
        self.thoughts.draw(surface, self.thinking, self.agent_name(mover), self.hover)
        self.new_game_button.draw(surface, font, self.hover)
        self.menu_button.draw(surface, font, self.hover)
