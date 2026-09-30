"""The Play window, without a real screen: clicks and keys become the right moves."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no real window during tests

import pygame
import pytest

from awale.engine import Game, Position, Side
from awale.ui.board_view import HEIGHT, WIDTH, pit_at, pit_center
from awale.ui.play import PlayScreen


@pytest.fixture
def screen():
    pygame.init()
    yield PlayScreen()
    pygame.quit()


def click(screen, side, pit):
    screen.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pit_center(side, pit), button=1))


def press(screen, key):
    screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def test_north_pit_1_is_top_right_and_south_pit_1_is_bottom_left():
    north_1, north_6 = pit_center(Side.NORTH, 1), pit_center(Side.NORTH, 6)
    south_1, south_6 = pit_center(Side.SOUTH, 1), pit_center(Side.SOUTH, 6)

    assert north_1[1] < south_1[1]  # North is on top
    assert north_1[0] > north_6[0]  # North counts from the right of the screen
    assert south_1[0] < south_6[0]  # South counts from the left
    assert north_1[0] == south_6[0]  # North's pit 1 is across from South's pit 6


def test_pit_at_finds_every_pit_and_nothing_between_them():
    for side in Side:
        for pit in range(1, 7):
            assert pit_at(pit_center(side, pit)) == (side, pit)
    assert pit_at((5, 5)) is None


def test_clicking_a_pit_in_your_row_plays_it(screen):
    click(screen, Side.SOUTH, 3)

    assert screen.game.moves == [3]
    assert screen.game.position.to_move is Side.NORTH


def test_clicking_the_opponents_row_does_nothing(screen):
    click(screen, Side.NORTH, 3)

    assert screen.game.moves == []


def test_keys_count_from_the_left_of_the_player_to_move(screen):
    press(screen, pygame.K_2)  # South's pit 2
    press(screen, pygame.K_KP5)  # North's pit 5, from the number pad

    assert screen.game.moves == [2, 5]
    assert screen.game.position.pits(Side.NORTH) == (4, 4, 4, 4, 0, 5)


def test_an_empty_pit_cannot_be_played(screen):
    screen.game = Game(start=Position.setup(south=(0, 1, 1, 1, 1, 1), north=(4, 4, 4, 4, 4, 4)))

    press(screen, pygame.K_1)
    click(screen, Side.SOUTH, 1)

    assert screen.game.moves == []


def test_a_capture_is_shown_in_the_message(screen):
    screen.game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(1, 2, 4, 4, 4, 4)))

    press(screen, pygame.K_6)  # makes North's pits 1 and 2 hold 2 and 3

    assert screen.message == "South captured 5 seeds."


def test_status_shows_the_winner_and_n_starts_a_new_game(screen):
    screen.game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4), stores=(23, 0)))
    press(screen, pygame.K_6)

    assert screen.status() == "South wins, 25 to 21"
    press(screen, pygame.K_1)
    assert screen.game.moves == [6]  # no moves after the game is over

    press(screen, pygame.K_n)
    assert screen.game.moves == []
    assert screen.status() == "South to move"


def test_drawing_works_during_and_after_a_game(screen):
    surface = pygame.Surface((WIDTH, HEIGHT))
    screen.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pit_center(Side.SOUTH, 1)))
    screen.draw(surface)

    screen.game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4), stores=(23, 0)))
    press(screen, pygame.K_6)
    screen.draw(surface)
