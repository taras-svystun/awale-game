"""The start menu: pick who plays South and North, and who moves first."""

import pygame

from awale.agents import AGENTS
from awale.engine import Side
from awale.ui.board_view import BACKGROUND, HEIGHT, TEXT, TEXT_SOFT, WIDTH
from awale.ui.play import PERSON, PlayScreen
from awale.ui.widgets import Button, blit_centered

ROW_Y = {Side.SOUTH: 190, Side.NORTH: 260, "first": 330}
LABEL_RIGHT, OPTIONS_X = 370, 400
OPTION_WIDTH, OPTION_GAP, OPTION_HEIGHT = 150, 16, 46


def option_rect(row, i: int) -> pygame.Rect:
    return pygame.Rect(OPTIONS_X + i * (OPTION_WIDTH + OPTION_GAP), ROW_Y[row] - OPTION_HEIGHT // 2, OPTION_WIDTH, OPTION_HEIGHT)


class MenuScreen:
    def __init__(self, choices: dict[Side, str] | None = None, first: Side = Side.SOUTH):
        # For each side, PERSON or the name of an AI agent from AGENTS.
        self.choices = choices or {Side.SOUTH: PERSON, Side.NORTH: "Random"}
        self.first = first
        self.hover: tuple[int, int] | None = None
        self.font_title = pygame.font.Font(None, 72)
        self.font = pygame.font.Font(None, 30)
        self.player_buttons = {
            (side, name): Button(option_rect(side, i), name)
            for side in Side
            for i, name in enumerate([PERSON, *AGENTS])
        }
        self.first_buttons = {side: Button(option_rect("first", i), side.name.title()) for i, side in enumerate(Side)}
        self.start_button = Button(pygame.Rect((WIDTH - 220) // 2, 410, 220, 54), "Start (Enter)")

    @property
    def can_start(self) -> bool:
        # Play needs at least one person. An AI against an AI is Watch, which comes later.
        return PERSON in self.choices.values()

    def handle(self, event: pygame.event.Event):
        """React to one event. Returns the screen to show next: this menu, or the game once it starts."""
        if event.type == pygame.MOUSEMOTION:
            self.hover = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for (side, name), button in self.player_buttons.items():
                if button.contains(event.pos):
                    self.choices[side] = name
            for side, button in self.first_buttons.items():
                if button.contains(event.pos):
                    self.first = side
            if self.start_button.contains(event.pos):
                return self.start()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self.start()
        return self

    def start(self):
        if not self.can_start:
            return self
        players = {side: None if name == PERSON else AGENTS[name]() for side, name in self.choices.items()}
        return PlayScreen(players, self.first)

    def update(self) -> None:
        pass  # nothing moves on its own in the menu

    @property
    def wants_hand_cursor(self) -> bool:
        if not self.hover:
            return False
        buttons = [*self.player_buttons.values(), *self.first_buttons.values()]
        if self.can_start:
            buttons.append(self.start_button)
        return any(button.contains(self.hover) for button in buttons)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        blit_centered(surface, self.font_title, "Awalé", TEXT, (WIDTH // 2, 80))
        labels = {Side.SOUTH: "South (bottom)", Side.NORTH: "North (top)", "first": "Moves first"}
        for row, label in labels.items():
            image = self.font.render(label, True, TEXT_SOFT)
            surface.blit(image, image.get_rect(midright=(LABEL_RIGHT, ROW_Y[row])))
        for (side, name), button in self.player_buttons.items():
            button.draw(surface, self.font, self.hover, selected=self.choices[side] == name)
        for side, button in self.first_buttons.items():
            button.draw(surface, self.font, self.hover, selected=self.first is side)
        self.start_button.draw(surface, self.font, self.hover, enabled=self.can_start)
        if not self.can_start:
            note = "At least one player must be a person. AI against AI comes later, in Watch."
            blit_centered(surface, self.font, note, TEXT_SOFT, (WIDTH // 2, 500))
