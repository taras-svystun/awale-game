"""Play: two people share one computer and take turns at the same window."""

import pygame

from awale.engine import Game, Side
from awale.ui.board_view import BACKGROUND, HEIGHT, TEXT, TEXT_SOFT, WIDTH, BoardView, pit_at

PIT_KEYS = {
    **{getattr(pygame, f"K_{n}"): n for n in range(1, 7)},
    **{getattr(pygame, f"K_KP{n}"): n for n in range(1, 7)},
}
HELP = "Click a pit or press 1-6 (from your own left).    N: new game    Esc: quit"


class PlayScreen:
    """One Play game: turns clicks and key presses into moves, and draws the window."""

    def __init__(self):
        self.view = BoardView()
        self.game = Game()
        self.message = ""
        self.hover: tuple[Side, int] | None = None

    @property
    def playable(self) -> list[int]:
        return [] if self.game.is_over else self.game.position.legal_moves()

    def handle(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hover = pit_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = pit_at(event.pos)
            if clicked and clicked[0] is self.game.position.to_move:
                self.try_move(clicked[1])
        elif event.type == pygame.KEYDOWN:
            if event.key in PIT_KEYS:
                self.try_move(PIT_KEYS[event.key])
            elif event.key == pygame.K_n:
                self.game = Game()
                self.message = ""

    def try_move(self, pit: int) -> None:
        """Play `pit` for the player to move. Does nothing if that move is not allowed."""
        if pit not in self.playable:
            return
        mover = self.game.position.to_move
        store_before = self.game.position.store(mover)
        self.game.play(pit)
        # When the game ends, the stores also get the seeds left in each row, so that is not a capture.
        captured = self.game.position.store(mover) - store_before
        self.message = f"{mover.name.title()} captured {captured} seeds." if captured and not self.game.is_over else ""

    @property
    def is_hovering_playable_pit(self) -> bool:
        return bool(self.hover) and self.hover[0] is self.game.position.to_move and self.hover[1] in self.playable

    def status(self) -> str:
        result = self.game.result
        if result is None:
            return f"{self.game.position.to_move.name.title()} to move"
        south, north = result.score
        if result.winner is None:
            return f"Draw, {south} to {north}"
        high, low = max(south, north), min(south, north)
        return f"{result.winner.name.title()} wins, {high} to {low}"

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        last_move = None
        if self.game.moves:
            # The player who moved last is the one not to move now.
            last_move = (self.game.position.to_move.opponent, self.game.moves[-1])
        self.view.draw(surface, self.game.position, self.playable, self.hover, last_move)
        self._blit_centered(surface, self.view.font_big, self.status(), TEXT, (WIDTH // 2, 35))
        self._blit_centered(surface, self.view.font_small, self.message, TEXT_SOFT, (WIDTH // 2, 68))
        self._blit_centered(surface, self.view.font_small, HELP, TEXT_SOFT, (WIDTH // 2, HEIGHT - 45))

    @staticmethod
    def _blit_centered(surface, font, text, color, center) -> None:
        image = font.render(text, True, color)
        surface.blit(image, image.get_rect(center=center))


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Awalé")
    surface = pygame.display.set_mode((WIDTH, HEIGHT))
    screen = PlayScreen()
    clock = pygame.time.Clock()
    hand_cursor = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            screen.handle(event)
        if screen.is_hovering_playable_pit != hand_cursor:
            hand_cursor = screen.is_hovering_playable_pit
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hand_cursor else pygame.SYSTEM_CURSOR_ARROW)
        screen.draw(surface)
        pygame.display.flip()
        clock.tick(30)
