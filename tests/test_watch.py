"""Watch: two AI agents play each other in a window, with their thoughts. Tested without a real screen."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no real window during tests

import threading

import pygame
import pytest

from awale.agents import Agent, RandomAgent, Thoughts
from awale.engine import Game, Position, Side
from awale.records import load_game
from awale.ui.board_view import HEIGHT, WIDTH
from awale.ui.menu import PERSON, MenuScreen
from awale.ui.play import PlayScreen
from awale.ui.thoughts_view import line_text, score_text
from awale.ui.watch import FASTEST, SLOWEST, WatchScreen, delay_at, value_for


class ScoringAgent(Agent):
    """A test agent with thoughts: it plays its leftmost pit, and scores each pit by its number."""

    name = "Scoring"

    def think(self, position):
        moves = position.legal_moves()
        return Thoughts(moves[0], scores={pit: pit for pit in moves}, line=(moves[0], 6), positions=7, depth=2)


class WaitingAgent(ScoringAgent):
    """Thinks until the test lets it answer."""

    def __init__(self):
        super().__init__()
        self.may_answer = threading.Event()

    def think(self, position):
        self.may_answer.wait(timeout=5)
        return super().think(position)


@pytest.fixture(autouse=True)
def pygame_running():
    pygame.init()
    yield
    pygame.quit()


def watch(south=None, north=None, delay=0) -> WatchScreen:
    return WatchScreen({Side.SOUTH: south or ScoringAgent(), Side.NORTH: north or ScoringAgent()}, delay=delay)


def let_agent_think(screen):
    screen.update()  # the agent starts thinking in its own thread
    screen.thinking.wait()


def next_move(screen):
    let_agent_think(screen)
    screen.update()  # its move is played, if it is time


def press(screen, key):
    return screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def click(screen, point):
    return screen.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=1))


def test_the_agents_take_turns():
    screen = watch()

    next_move(screen)
    next_move(screen)

    assert screen.game.moves == [1, 1]
    assert screen.message == "North (Scoring) played pit 1."


def test_the_thoughts_are_about_the_position_on_the_board():
    screen = watch(delay=60)

    let_agent_think(screen)
    screen.update()

    assert screen.game.moves == []  # the move waits, so you can read the thoughts first
    assert screen.thinking.position == screen.game.position
    assert screen.thinking.thoughts.scores == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
    assert screen.status() == "South (Scoring) chose pit 1"


def test_pause_stops_the_game_and_space_resumes_it():
    screen = watch()
    press(screen, pygame.K_SPACE)

    next_move(screen)
    assert screen.game.moves == []
    assert screen.status() == "Paused. South (Scoring) chose pit 1"

    press(screen, pygame.K_SPACE)
    screen.update()
    assert screen.game.moves == [1]


def test_step_plays_one_move_and_stays_paused():
    screen = watch(delay=60)

    press(screen, pygame.K_s)
    next_move(screen)
    next_move(screen)

    assert screen.game.moves == [1]
    assert screen.paused


def test_step_asked_while_the_agent_thinks_plays_when_it_is_done():
    agent = WaitingAgent()
    screen = watch(south=agent)
    press(screen, pygame.K_SPACE)
    screen.update()  # the agent starts thinking

    click(screen, screen.step_button.rect.center)
    agent.may_answer.set()
    screen.thinking.wait()
    screen.update()

    assert screen.game.moves == [1]


def test_the_speed_slider_sets_the_time_per_move():
    screen = watch(delay=1)
    slider = screen.speed.rect

    click(screen, slider.midright)
    assert screen.move_delay == pytest.approx(FASTEST)

    screen.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=slider.midleft, buttons=(1, 0, 0)))
    assert screen.move_delay == pytest.approx(SLOWEST)

    screen.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=slider.midleft, button=1))
    screen.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=slider.midright, buttons=(0, 0, 0)))
    assert screen.move_delay == pytest.approx(SLOWEST)  # the mouse let go of the knob


def test_the_slider_moves_evenly_from_slow_to_fast():
    assert delay_at(0) == pytest.approx(SLOWEST)
    assert delay_at(1) == pytest.approx(FASTEST)
    # Halfway, as a volume knob counts: 3 s divided by some number, and that times the same number gives 0.1 s.
    assert delay_at(0.5) == pytest.approx((SLOWEST * FASTEST) ** 0.5)
    assert value_for(delay_at(0.3)) == pytest.approx(0.3)


def test_each_part_of_the_thoughts_has_a_checkbox():
    screen = watch()
    boxes = screen.thoughts.checkboxes
    assert all(box.checked for box in boxes)

    click(screen, screen.thoughts.line_box.rect.center)

    assert [box.checked for box in boxes] == [True, False, True]


def test_the_line_of_play_is_written_in_move_letters():
    assert line_text(Side.SOUTH, (3, 4, 1)) == "c D a"
    assert line_text(Side.NORTH, (6, 2)) == "F b"


def test_scores_are_short():
    assert score_text(3) == "+3"
    assert score_text(-2.0) == "-2"
    assert score_text(0) == "0"
    assert score_text(0.5234) == "0.52"


def test_a_finished_watch_game_is_saved(records_in_a_temporary_folder):
    screen = watch(RandomAgent(seed=1), RandomAgent(seed=2))
    while not screen.game.is_over:
        next_move(screen)

    [saved] = (records_in_a_temporary_folder / "games").iterdir()
    record = load_game(saved)
    assert (record.south, record.north) == ("Random", "Random")
    assert record.replay().positions == screen.game.positions


def test_n_starts_a_new_game_and_m_goes_back_to_the_menu():
    screen = watch()
    next_move(screen)

    press(screen, pygame.K_n)
    assert screen.game.moves == []

    menu = press(screen, pygame.K_m)
    assert isinstance(menu, MenuScreen)
    assert menu.choices == {Side.SOUTH: "Scoring", Side.NORTH: "Scoring"}


def test_watch_needs_two_ai_agents():
    with pytest.raises(ValueError, match="Play"):
        WatchScreen({Side.SOUTH: None, Side.NORTH: ScoringAgent()})


def test_the_menu_starts_watch_for_two_ai_agents_and_play_with_a_person():
    watch_screen = press(MenuScreen({Side.SOUTH: "Random", Side.NORTH: "Random"}, Side.NORTH), pygame.K_RETURN)
    play_screen = press(MenuScreen({Side.SOUTH: PERSON, Side.NORTH: "Random"}), pygame.K_RETURN)

    assert isinstance(watch_screen, WatchScreen)
    assert watch_screen.game.position.to_move is Side.NORTH
    assert isinstance(play_screen, PlayScreen)


def test_drawing_every_moment_of_a_watch_game():
    surface = pygame.Surface((WIDTH, HEIGHT))
    MenuScreen({Side.SOUTH: "Random", Side.NORTH: "Random"}).draw(surface)

    agent = WaitingAgent()
    screen = watch(south=agent, delay=60)
    screen.draw(surface)  # nobody is thinking yet
    screen.update()
    screen.draw(surface)  # thinking
    agent.may_answer.set()
    screen.thinking.wait()
    screen.draw(surface)  # thoughts with scores
    for box in screen.thoughts.checkboxes:
        box.checked = False
    screen.draw(surface)  # thoughts all hidden

    random_screen = watch(RandomAgent(seed=1), RandomAgent(seed=2))
    let_agent_think(random_screen)
    random_screen.draw(surface)  # an agent with no scores and no line

    random_screen.game = Game(start=Position.setup(south=(0, 0, 0, 0, 0, 2), north=(4, 1, 4, 4, 4, 4), stores=(23, 0)))
    random_screen.thinking = None
    next_move(random_screen)
    assert random_screen.game.is_over
    random_screen.draw(surface)  # the game is over
