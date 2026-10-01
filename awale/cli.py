"""The `awale` command. Each way to use the game is a subcommand."""

import argparse
import sys

from awale.agents import AGENTS, HEURISTICS, make_agent
from awale.engine import Side
from awale.tournament import OPENING_MOVES, OPENINGS, run_tournament


def agent_name(name: str) -> str:
    """Check an agent name on the command line, so a typo is reported before anything starts."""
    try:
        make_agent(name)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None
    return name


AGENT_NAMES = (
    f"one of {', '.join(AGENTS)}; "
    f"Minimax, AlphaBeta, Deepening and OpenSpielAlphaBeta can also take a depth and a heuristic ({', '.join(HEURISTICS)}), "
    "like AlphaBeta:8 or AlphaBeta:8:mix; "
    "Deepening, MCTS and OpenSpielMCTS can also take a time limit per move, like Deepening:0.5s:mix or MCTS:1s; "
    "MCTS and OpenSpielMCTS can also take a number of playouts per move, like MCTS:1000"
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="awale", description="Awalé: play people or AI, and compare AI agents.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("play", help="Open a window to play: two people on one computer, or a person against an AI.")

    watch = commands.add_parser(
        "watch",
        help="Open a window where two AI agents play each other, with their thoughts next to the board.",
    )
    watch.add_argument("south", type=agent_name, help=f"the agent playing South (at the bottom): {AGENT_NAMES}")
    watch.add_argument("north", type=agent_name, help="the agent playing North (at the top)")
    watch.add_argument("--first", choices=["south", "north"], default="south", help="who moves first (default south)")

    tournament = commands.add_parser(
        "tournament",
        help="Play many games between two AI agents, with no window, and compare them.",
        description="Each random opening is played twice, with the agents swapping sides.",
    )
    tournament.add_argument("a", type=agent_name, help=f"agent A: {AGENT_NAMES}")
    tournament.add_argument("b", type=agent_name, help="agent B")
    tournament.add_argument("--openings", type=int, default=OPENINGS, help=f"how many random openings (default {OPENINGS}); there are two games per opening")
    tournament.add_argument("--opening-moves", type=int, default=OPENING_MOVES, help=f"random moves in each opening (default {OPENING_MOVES})")
    tournament.add_argument("--seed", type=int, help="the same seed plays exactly the same games again")
    tournament.add_argument("--workers", type=int, help="how many processes (default: one per CPU core)")
    tournament.add_argument("--save", action="store_true", help="save every game in a CSV file in records/tournaments")
    args = parser.parse_args()

    if args.command == "play":
        from awale.ui.app import run  # imported here so the other commands never load Pygame

        run()
    elif args.command == "watch":
        from awale.ui.app import run
        from awale.ui.watch import WatchScreen

        players = {Side.SOUTH: make_agent(args.south), Side.NORTH: make_agent(args.north)}
        run(lambda: WatchScreen(players, Side[args.first.upper()]))
    elif args.command == "tournament":
        run_tournament_command(args)


def run_tournament_command(args: argparse.Namespace) -> None:
    def show_progress(done: int, total: int) -> None:
        if done % max(1, total // 100) and done != total:
            return  # only every 1%, so the screen is not flooded
        # "\r" goes back to the start of the line, so the count updates in place.
        print(f"\rPlayed {done} of {total} games", end="", file=sys.stderr, flush=True)

    tournament = run_tournament(
        args.a, args.b, args.openings, args.opening_moves, args.seed, args.workers, on_progress=show_progress
    )
    print(file=sys.stderr)
    print()
    print(tournament.report())
    if args.save:
        print(f"\nSaved to {tournament.save()}")
