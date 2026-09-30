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
