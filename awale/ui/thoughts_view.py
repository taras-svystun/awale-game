"""The thoughts panel: what an AI agent shows about how it chose its move.

It has a checkbox for each part:
- move scores, drawn over the pits of the player to move, the chosen move in yellow,
  and "≤" before a score that is only an upper bound;
- the expected line of play, in move letters (a-f South, A-F North);
- the work done: positions looked at, how deep, and how long it took.
"""

import time

import pygame

from awale.agents import Thoughts
from awale.engine import Side
from awale.records import move_letter
from awale.tournament import duration
from awale.ui.agent_thread import AgentThread
from awale.ui.board_view import HOVER, PIT, ROW_Y, TEXT, TEXT_SOFT, WIDTH, pit_center
from awale.ui.widgets import BUTTON_TEXT_SELECTED, Checkbox, blit_centered

# Scores sit in the gap between the two rows, next to the row of the player to move.
GAP_Y = (ROW_Y[Side.NORTH] + ROW_Y[Side.SOUTH]) // 2
SCORE_Y = {Side.NORTH: GAP_Y - 14, Side.SOUTH: GAP_Y + 14}
SCORE_WIDTH, SCORE_HEIGHT = 60, 24
LEFT = 60


def score_text(score: float, upper_bound: bool = False) -> str:
    """+3, -2 and 0 for whole numbers (like seeds), 0.52 for the rest (like a share of wins).

    An upper bound gets a "≤" in front: the move is worth this or less.
    """
    if float(score).is_integer():
        text = f"{score:+.0f}" if score else "0"
    else:
        text = f"{score:.2f}"
    return f"≤{text}" if upper_bound else text


def line_text(first_mover: Side, line: tuple[int, ...]) -> str:
    """The pits of a line of play as move letters. Players take turns, so the sides alternate."""
    letters = []
    side = first_mover
    for pit in line:
        letters.append(move_letter(side, pit))
        side = side.opponent
    return " ".join(letters)


def work_text(thoughts: Thoughts, seconds: float) -> str:
    return f"{thoughts.positions:,} positions, depth {thoughts.depth}, {duration(seconds)}"


class ThoughtsPanel:
    def __init__(self, top: int, checked: bool = True):
        self.top = top
        labels = ["Move scores", "Expected line", "Work done"]
        self.scores_box, self.line_box, self.work_box = (
            Checkbox(pygame.Rect(LEFT + i * 220, top, 200, 30), label, checked) for i, label in enumerate(labels)
        )
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 22)

    @property
    def checkboxes(self) -> list[Checkbox]:
        return [self.scores_box, self.line_box, self.work_box]

    def handle_click(self, point: tuple[int, int]) -> None:
        for box in self.checkboxes:
            box.handle_click(point)

    def draw(self, surface: pygame.Surface, thinking: AgentThread | None, agent_name: str, hover=None) -> None:
        """Draw the checkboxes, and the parts of `thinking`'s thoughts that are checked.

        `thinking` is the agent choosing a move in the position on the board, or None when nobody is.
        """
        for box in self.checkboxes:
            box.draw(surface, self.font, hover)
        if thinking is None:
            return
        line_y, work_y = self.top + 50, self.top + 80
        if not thinking.is_done:
            if self.work_box.checked:
                waited = time.monotonic() - thinking.started
                self._text(surface, f"Work done: thinking for {duration(waited)}...", work_y)
            return
        thoughts = thinking.thoughts
        mover = thinking.position.to_move
        if self.scores_box.checked:
            self._draw_scores(surface, thoughts, mover, agent_name)
        if self.line_box.checked:
            line = line_text(mover, thoughts.line) if thoughts.line else f"{agent_name} does not give one"
            self._text(surface, f"Expected line: {line}", line_y)
        if self.work_box.checked:
            self._text(surface, f"Work done: {work_text(thoughts, thinking.seconds)}", work_y)

    def _draw_scores(self, surface: pygame.Surface, thoughts: Thoughts, mover: Side, agent_name: str) -> None:
        if not thoughts.scores:
            note = f"{agent_name} gives no move scores"
            blit_centered(surface, self.font_small, note, TEXT_SOFT, (WIDTH // 2, SCORE_Y[mover]))
            return
        for pit, score in thoughts.scores.items():
            chosen = pit == thoughts.move
            badge = pygame.Rect(0, 0, SCORE_WIDTH, SCORE_HEIGHT)
            badge.center = (pit_center(mover, pit)[0], SCORE_Y[mover])
            pygame.draw.rect(surface, HOVER if chosen else PIT, badge, border_radius=SCORE_HEIGHT // 2)
            color = BUTTON_TEXT_SELECTED if chosen else TEXT
            text = score_text(score, pit in thoughts.upper_bounds)
            blit_centered(surface, self.font, text, color, badge.center)

    def _text(self, surface: pygame.Surface, text: str, y: int) -> None:
        image = self.font.render(text, True, TEXT)
        surface.blit(image, image.get_rect(midleft=(LEFT, y)))
