"""Play against an AI agent, and the start menu, without a real screen."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no real window during tests

import threading

import pygame
import pytest

from awale.agents import AGENTS, HEURISTICS, Agent, AlphaBetaAgent, DeepeningAgent, MCTSAgent, RandomAgent
from awale.engine import Side
from awale.ui.board_view import HEIGHT, WIDTH, pit_center
from awale.ui.menu import PERSON, MenuScreen
from awale.ui.play import PlayScreen


class FirstMoveAgent(Agent):
    """A test agent that always plays its leftmost legal pit, so the tests know what it will do."""

    name = "First"

    def choose_move(self, position):
        return position.legal_moves()[0]


class WaitingAgent(FirstMoveAgent):
    """Thinks until the test lets it answer, to test what happens while an AI is thinking."""

    def __init__(self):
        self.may_answer = threading.Event()

    def choose_move(self, position):
        self.may_answer.wait(timeout=5)
        return super().choose_move(position)


class BrokenAgent(Agent):
    def choose_move(self, position):
        raise RuntimeError("this agent is broken")


@pytest.fixture(autouse=True)
def pygame_running():
    pygame.init()
    yield
    pygame.quit()


def against(agent, person=Side.SOUTH, first=Side.SOUTH) -> PlayScreen:
    return PlayScreen({person: None, person.opponent: agent}, first, ai_move_delay=0)


def let_ai_move(screen):
    screen.update()  # the agent starts thinking in its own thread
    screen.thinking.wait()
    screen.update()  # its move is played


def click(screen, point):
    screen.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=1))


def press(screen, key):
    return screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def test_the_ai_answers_the_persons_move():
    screen = against(FirstMoveAgent())

    click(screen, pit_center(Side.SOUTH, 3))
    assert screen.status() == "North (First) is thinking..."
    let_ai_move(screen)

    assert screen.game.moves == [3, 1]
    assert screen.message == "North (First) played pit 1."
    assert screen.status() == "South to move"


def test_the_ai_can_move_first():
    screen = against(FirstMoveAgent(), person=Side.NORTH, first=Side.SOUTH)

    let_ai_move(screen)

    assert screen.game.moves == [1]
    assert screen.game.position.to_move is Side.NORTH


def test_the_person_cannot_move_for_the_ai():
    screen = against(FirstMoveAgent(), person=Side.NORTH, first=Side.SOUTH)

    assert screen.playable == []
    press(screen, pygame.K_1)
    click(screen, pit_center(Side.SOUTH, 1))

    assert screen.game.moves == []


def test_the_ai_waits_a_moment_so_you_see_your_own_move_first():
    screen = PlayScreen({Side.SOUTH: None, Side.NORTH: FirstMoveAgent()}, ai_move_delay=60)

    press(screen, pygame.K_3)
    screen.update()
    screen.thinking.wait()
    screen.update()

    assert screen.game.moves == [3]


def test_undo_against_the_ai_goes_back_to_your_last_turn():
    screen = against(FirstMoveAgent())
    press(screen, pygame.K_3)
    let_ai_move(screen)
    press(screen, pygame.K_2)
    let_ai_move(screen)

    press(screen, pygame.K_u)

    assert screen.game.moves == [3, 1]
    assert screen.game.position.to_move is Side.SOUTH


def test_undo_while_the_ai_is_thinking_takes_back_your_move_and_drops_its_answer():
    agent = WaitingAgent()
    screen = against(agent)
    press(screen, pygame.K_3)
    screen.update()  # the agent starts thinking

    press(screen, pygame.K_u)
    agent.may_answer.set()
    screen.update()

    assert screen.game.moves == []
    assert screen.thinking is None


def test_undo_does_nothing_before_your_first_move():
    screen = against(FirstMoveAgent(), person=Side.NORTH, first=Side.SOUTH)
    let_ai_move(screen)

    press(screen, pygame.K_u)

    assert screen.game.moves == [1]


def test_a_broken_agent_stops_the_program_instead_of_hanging():
    screen = against(BrokenAgent())
    press(screen, pygame.K_3)
    screen.update()
    screen.thinking.wait()

    with pytest.raises(RuntimeError, match="broken"):
        screen.update()


def test_the_menu_starts_a_game_with_the_chosen_players():
    menu = MenuScreen()
    click(menu, menu.player_buttons[(Side.SOUTH, "Random")].rect.center)
    click(menu, menu.player_buttons[(Side.NORTH, PERSON)].rect.center)
    click(menu, menu.first_buttons[Side.NORTH].rect.center)

    screen = press(menu, pygame.K_RETURN)

    assert isinstance(screen, PlayScreen)
    assert isinstance(screen.players[Side.SOUTH], RandomAgent)
    assert screen.players[Side.NORTH] is None
    assert screen.game.position.to_move is Side.NORTH


def test_the_menu_offers_every_ai_agent_and_every_button_fits_in_the_window():
    menu = MenuScreen()
    window = pygame.Rect(0, 0, WIDTH, HEIGHT)

    # Plain Deepening is left out: with store_diff it is only a quicker AlphaBeta.
    offered = {PERSON, *(set(AGENTS) - {"Deepening"}), "AlphaBeta:mix", "Deepening:mix"}
    assert {name for _, name in menu.player_buttons} == offered
    for button in [*menu.player_buttons.values(), *menu.first_buttons.values(), menu.start_button]:
        assert window.contains(button.rect), button.label
        assert menu.font_small.size(button.label)[0] < button.rect.width - 8, button.label  # the name fits

    click(menu, menu.player_buttons[(Side.NORTH, "AlphaBeta")].rect.center)
    screen = press(menu, pygame.K_RETURN)
    assert isinstance(screen.players[Side.NORTH], AlphaBetaAgent)

    menu = MenuScreen()
    click(menu, menu.player_buttons[(Side.NORTH, "AlphaBeta:mix")].rect.center)
    screen = press(menu, pygame.K_RETURN)
    assert screen.players[Side.NORTH].heuristic is HEURISTICS["mix"]

    menu = MenuScreen()
    click(menu, menu.player_buttons[(Side.NORTH, "Deepening:mix")].rect.center)
    screen = press(menu, pygame.K_RETURN)
    assert isinstance(screen.players[Side.NORTH], DeepeningAgent)
    assert screen.players[Side.NORTH].heuristic is HEURISTICS["mix"]
    assert screen.players[Side.NORTH].time_limit == 0.1

    menu = MenuScreen()
    click(menu, menu.player_buttons[(Side.NORTH, "MCTS")].rect.center)
    screen = press(menu, pygame.K_RETURN)
    assert isinstance(screen.players[Side.NORTH], MCTSAgent)
    assert screen.players[Side.NORTH].time_limit == 0.1


def test_back_to_the_menu_keeps_the_choices():
    screen = PlayScreen({Side.SOUTH: None, Side.NORTH: RandomAgent()}, first=Side.NORTH)

    menu = press(screen, pygame.K_m)

    assert isinstance(menu, MenuScreen)
    assert menu.choices == {Side.SOUTH: PERSON, Side.NORTH: "Random"}
    assert menu.first is Side.NORTH


def test_drawing_the_menu_and_a_game_against_ai():
    surface = pygame.Surface((WIDTH, HEIGHT))
    MenuScreen().draw(surface)
    MenuScreen({Side.SOUTH: "Random", Side.NORTH: "Random"}).draw(surface)
    screen = against(FirstMoveAgent())
    press(screen, pygame.K_3)
    screen.draw(surface)
