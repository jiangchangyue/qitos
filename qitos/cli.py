"""Top-level qit CLI."""

from __future__ import annotations

import argparse
import sys

from qitos.kit.skill.cli import main as skill_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qit", description="QitOS developer CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("skill", help="Manage third-party skills")
    ns, remaining = parser.parse_known_args(argv)
    if ns.command == "skill":
        return skill_main(remaining)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
