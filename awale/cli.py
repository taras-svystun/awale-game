"""The `awale` command. Each way to use the game is a subcommand."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="awale", description="Awalé: play people or AI, and compare AI agents.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("play", help="Open a window where two people play on one computer.")
    args = parser.parse_args()

    if args.command == "play":
        from awale.ui.play import run  # imported here so the other commands never load Pygame

        run()
