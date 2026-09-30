"""Where things are on the screen, and how to draw the board.

South's row is at the bottom, pits 1-6 from left to right.
North's row is at the top. North sits on the far side of the board,
so North's pit 1 (on North's own left) is at the top right.
Sowing then goes counter-clockwise on the screen, as on a real board.
"""

import math

import pygame

from awale.engine import PITS_PER_ROW, Position, Side

WIDTH, HEIGHT = 1000, 520

BOARD = pygame.Rect(40, 90, 920, 340)
PIT_RADIUS = 50
SEED_RADIUS = 4
FIRST_PIT_X = 220
PIT_SPACING = 112
ROW_Y = {Side.NORTH: 180, Side.SOUTH: 340}
# Each player's store is on their own right: South's on the screen right, North's on the left.
STORE = {
    Side.NORTH: pygame.Rect(58, 125, 95, 270),
    Side.SOUTH: pygame.Rect(847, 125, 95, 270),
}

BACKGROUND = (28, 38, 33)
WOOD = (139, 94, 52)
WOOD_DARK = (96, 62, 30)
ROW_TO_MOVE = (163, 115, 68)
PIT = (74, 46, 20)
SEED = (240, 228, 205)
SEED_SHADOW = (60, 36, 14)
DIM = (0, 0, 0, 110)
HOVER = (250, 214, 90)
LAST_MOVE = (230, 130, 60)
TEXT = (240, 236, 225)
TEXT_SOFT = (175, 168, 150)


def pit_center(side: Side, pit: int) -> tuple[int, int]:
    """Screen point at the middle of `pit` (1-6, from the owner's own left)."""
    column = pit - 1 if side is Side.SOUTH else PITS_PER_ROW - pit
    return FIRST_PIT_X + column * PIT_SPACING, ROW_Y[side]


def pit_at(point: tuple[int, int]) -> tuple[Side, int] | None:
    """Which pit is under a screen point, or None if it is not on a pit."""
    for side in Side:
        for pit in range(1, PITS_PER_ROW + 1):
            x, y = pit_center(side, pit)
            if math.dist(point, (x, y)) <= PIT_RADIUS:
                return side, pit
    return None


class BoardView:
    def __init__(self):
        self.font_big = pygame.font.Font(None, 40)
        self.font = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 24)

    def draw(
        self,
        surface: pygame.Surface,
        position: Position,
        playable: list[int],
        hover: tuple[Side, int] | None = None,
        last_move: tuple[Side, int] | None = None,
    ) -> None:
        """Draw the board. `playable` are the pits the player to move may click."""
        pygame.draw.rect(surface, WOOD, BOARD, border_radius=40)
        pygame.draw.rect(surface, WOOD_DARK, BOARD, width=4, border_radius=40)
        self._draw_row_to_move(surface, position.to_move)
        for side in Side:
            self._draw_store(surface, side, position.store(side))
            for pit, seeds in enumerate(position.pits(side), start=1):
                can_play = side is position.to_move and pit in playable
                self._draw_pit(surface, side, pit, seeds, dimmed=not can_play)
                self._draw_pit_number(surface, side, pit)
        if last_move:
            pygame.draw.circle(surface, LAST_MOVE, pit_center(*last_move), PIT_RADIUS + 3, width=3)
        if hover and hover[0] is position.to_move and hover[1] in playable:
            pygame.draw.circle(surface, HOVER, pit_center(*hover), PIT_RADIUS + 3, width=4)

    def _draw_row_to_move(self, surface: pygame.Surface, side: Side) -> None:
        left = pit_center(Side.SOUTH, 1)[0] - PIT_RADIUS - 10
        right = pit_center(Side.SOUTH, PITS_PER_ROW)[0] + PIT_RADIUS + 10
        top = ROW_Y[side] - PIT_RADIUS - 10
        band = pygame.Rect(left, top, right - left, 2 * PIT_RADIUS + 20)
        pygame.draw.rect(surface, ROW_TO_MOVE, band, border_radius=PIT_RADIUS + 10)

    def _draw_pit(self, surface: pygame.Surface, side: Side, pit: int, seeds: int, dimmed: bool) -> None:
        cx, cy = pit_center(side, pit)
        pygame.draw.circle(surface, PIT, (cx, cy), PIT_RADIUS)
        # Seeds sit on a sunflower spiral around an empty middle, where the count goes.
        golden_angle = math.pi * (3 - math.sqrt(5))
        for i in range(seeds):
            r = min(18 + 4.6 * math.sqrt(i), PIT_RADIUS - SEED_RADIUS - 2)
            x = cx + r * math.cos(i * golden_angle)
            y = cy + r * math.sin(i * golden_angle)
            pygame.draw.circle(surface, SEED_SHADOW, (x + 1, y + 1), SEED_RADIUS)
            pygame.draw.circle(surface, SEED, (x, y), SEED_RADIUS)
        if seeds:
            self._blit_centered(surface, self.font, str(seeds), TEXT, (cx, cy))
        if dimmed:
            shade = pygame.Surface((2 * PIT_RADIUS, 2 * PIT_RADIUS), pygame.SRCALPHA)
            pygame.draw.circle(shade, DIM, (PIT_RADIUS, PIT_RADIUS), PIT_RADIUS)
            surface.blit(shade, (cx - PIT_RADIUS, cy - PIT_RADIUS))

    def _draw_pit_number(self, surface: pygame.Surface, side: Side, pit: int) -> None:
        x, y = pit_center(side, pit)
        # North's numbers go above its row, South's below, near the edge of the board.
        offset = PIT_RADIUS + 14
        y = y - offset if side is Side.NORTH else y + offset
        self._blit_centered(surface, self.font_small, str(pit), TEXT_SOFT, (x, y))

    def _draw_store(self, surface: pygame.Surface, side: Side, seeds: int) -> None:
        rect = STORE[side]
        pygame.draw.ellipse(surface, PIT, rect)
        self._blit_centered(surface, self.font_small, side.name.title(), TEXT_SOFT, (rect.centerx, rect.top + 40))
        self._blit_centered(surface, self.font_big, str(seeds), TEXT, rect.center)

    @staticmethod
    def _blit_centered(surface, font, text, color, center) -> None:
        image = font.render(text, True, color)
        surface.blit(image, image.get_rect(center=center))
