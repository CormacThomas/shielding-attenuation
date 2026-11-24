"""Dispatch command-line requests to the deterministic or OpenMC workflows."""

import argparse
import sys

from shielding.cli import benchmark, interactive, scenario


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shielding", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    scenario_parser = commands.add_parser(
        "scenario", help="Run a deterministic JSON case"
    )
    scenario.configure_parser(scenario_parser)
    scenario_parser.set_defaults(handler=scenario.run)

    benchmark_parser = commands.add_parser(
        "benchmark", help="Export, run, or process an OpenMC case"
    )
    benchmark.configure_parser(benchmark_parser)
    benchmark_parser.set_defaults(handler=benchmark.run)

    interactive_parser = commands.add_parser(
        "interactive", help="Open the interactive design menu"
    )
    interactive_parser.set_defaults(handler=run_interactive)

    arguments = parser.parse_args(argv)
    try:
        return arguments.handler(arguments)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"{arguments.command.capitalize()} failed: {error}", file=sys.stderr)
        return 1


def run_interactive(_arguments: argparse.Namespace) -> int:
    interactive.main()
    return 0
