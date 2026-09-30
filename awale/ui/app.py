"""The window's main loop. It shows one screen at a time: the start menu or a game."""

import pygame

from awale.ui.board_view import HEIGHT, WIDTH
from awale.ui.menu import MenuScreen


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Awalé")
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    screen = MenuScreen()
    clock = pygame.time.Clock()
    hand_cursor = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            screen = screen.handle(event)
        screen.update()
        if screen.wants_hand_cursor != hand_cursor:
            hand_cursor = screen.wants_hand_cursor
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hand_cursor else pygame.SYSTEM_CURSOR_ARROW)
        screen.draw(surface)
        pygame.display.flip()
        clock.tick(30)
