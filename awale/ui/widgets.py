"""Small pieces of the window that are not the board, like buttons."""

from dataclasses import dataclass

import pygame

from awale.ui.board_view import HOVER, PIT, TEXT, TEXT_SOFT, WOOD, WOOD_DARK

BUTTON_TEXT_SELECTED = (40, 28, 12)


@dataclass
class Button:
    rect: pygame.Rect
    label: str

    def contains(self, point: tuple[int, int]) -> bool:
        return self.rect.collidepoint(point)

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        hover: tuple[int, int] | None = None,
        selected: bool = False,
        enabled: bool = True,
    ) -> None:
        if not enabled:
            fill, border, color = PIT, WOOD_DARK, TEXT_SOFT
        elif selected:
            fill, border, color = HOVER, HOVER, BUTTON_TEXT_SELECTED
        else:
            fill, border, color = WOOD, WOOD_DARK, TEXT
        pygame.draw.rect(surface, fill, self.rect, border_radius=10)
        if enabled and hover and self.contains(hover):
            border = HOVER
        pygame.draw.rect(surface, border, self.rect, width=3, border_radius=10)
        image = font.render(self.label, True, color)
        surface.blit(image, image.get_rect(center=self.rect.center))


def blit_centered(surface: pygame.Surface, font: pygame.font.Font, text: str, color, center) -> None:
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=center))


@dataclass
class Checkbox:
    """A box you click to turn something on or off. The whole row, label included, can be clicked."""

    rect: pygame.Rect
    label: str
    checked: bool = False
    BOX = 22

    def contains(self, point: tuple[int, int]) -> bool:
        return self.rect.collidepoint(point)

    def handle_click(self, point: tuple[int, int]) -> None:
        if self.contains(point):
            self.checked = not self.checked

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, hover: tuple[int, int] | None = None) -> None:
        box = pygame.Rect(self.rect.left, self.rect.centery - self.BOX // 2, self.BOX, self.BOX)
        if self.checked:
            pygame.draw.rect(surface, HOVER, box, border_radius=4)
            tick = [(box.left + 5, box.centery), (box.left + 9, box.bottom - 5), (box.right - 4, box.top + 5)]
            pygame.draw.lines(surface, BUTTON_TEXT_SELECTED, False, tick, width=3)
        border = HOVER if hover and self.contains(hover) else TEXT_SOFT
        pygame.draw.rect(surface, border, box, width=2, border_radius=4)
        image = font.render(self.label, True, TEXT)
        surface.blit(image, image.get_rect(midleft=(box.right + 10, box.centery)))


@dataclass
class Slider:
    """A knob you drag along a line. `value` goes from 0.0 at the left end to 1.0 at the right end."""

    rect: pygame.Rect
    value: float = 0.5
    dragging: bool = False
    KNOB = 11

    def contains(self, point: tuple[int, int]) -> bool:
        # A little taller than the line itself, so it is easy to grab.
        return self.rect.inflate(2 * self.KNOB, 2 * self.KNOB).collidepoint(point)

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.contains(event.pos):
            self.dragging = True
            self._move_to(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._move_to(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def _move_to(self, x: int) -> None:
        self.value = min(1.0, max(0.0, (x - self.rect.left) / self.rect.width))

    def draw(self, surface: pygame.Surface, hover: tuple[int, int] | None = None) -> None:
        pygame.draw.line(surface, WOOD_DARK, self.rect.midleft, self.rect.midright, width=6)
        knob_x = self.rect.left + round(self.value * self.rect.width)
        pygame.draw.line(surface, WOOD, self.rect.midleft, (knob_x, self.rect.centery), width=6)
        active = self.dragging or (hover and self.contains(hover))
        pygame.draw.circle(surface, HOVER if active else TEXT, (knob_x, self.rect.centery), self.KNOB)
