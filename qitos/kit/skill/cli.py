"""CLI commands for QitOS skill management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .manager import SkillManager
from .manifest import SkillManifest, validate_skill_structure
from .registry import SkillRegistry


def build_parser(prog: str = "qit skill") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="Manage QitOS skills")
    parser.add_argument("--workspace", help="Workspace root for workspace-scoped skills")
    parser.add_argument("--provider", default="skillhub", help="Default skill provider (default: skillhub)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search skills from a provider catalog")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.set_defaults(func=cmd_search)

    install_parser = subparsers.add_parser("install", help="Install a skill")
    install_parser.add_argument("source", help="Provider ref like skillhub:github, slug, URL, or path")
    install_parser.add_argument("--activate", action="store_true", help="Activate immediately after install")
    install_parser.set_defaults(func=cmd_install)

    list_parser = subparsers.add_parser("list", help="List installed skills")
    list_parser.add_argument("--active-only", action="store_true")
    list_parser.set_defaults(func=cmd_list)

    info_parser = subparsers.add_parser("info", help="Show skill details")
    info_parser.add_argument("name", help="Skill ref, slug, or manifest name")
    info_parser.set_defaults(func=cmd_info)

    activate_parser = subparsers.add_parser("activate", help="Activate an installed skill")
    activate_parser.add_argument("name", help="Skill ref, slug, or manifest name")
    activate_parser.set_defaults(func=cmd_activate)

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove an installed skill")
    uninstall_parser.add_argument("name", help="Skill ref, slug, or manifest name")
    uninstall_parser.set_defaults(func=cmd_uninstall)

    validate_parser = subparsers.add_parser("validate", help="Validate a local skill directory")
    validate_parser.add_argument("path", help="Path to skill directory")
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def _manager(args: argparse.Namespace) -> SkillManager:
    return SkillManager(workspace_root=args.workspace, default_provider=args.provider)


def cmd_search(args: argparse.Namespace) -> int:
    manager = _manager(args)
    query = " ".join(args.query).strip()
    results = manager.search(query=query, limit=args.limit)
    if not results:
        print("No skills found.")
        return 0
    for result in results:
        header = f"{result.ref:<24} {result.version or '-':<12} {result.name}"
        print(header)
        if result.description:
            print(f"  {result.description}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    manager = _manager(args)
    installed = manager.install(args.source, activate=args.activate)
    status = "active" if installed.active else "installed"
    print(f"✓ {status} {installed.key} v{installed.package.version}")
    print(f"  {installed.manifest.description}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    registry = SkillRegistry(workspace_root=args.workspace)
    installed = registry.list_active() if args.active_only else registry.list_installed()
    if not installed:
        print("No skills installed.")
        return 0
    for item in installed:
        active = " [active]" if item.active else ""
        print(f"{item.key}{active} - {item.manifest.description}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    manager = _manager(args)
    installed = manager.get_installed(args.name)
    if installed is None:
        described = manager.describe(args.name)
        if described is None:
            print(f"Error: Skill '{args.name}' not found", file=sys.stderr)
            return 1
        print(f"Ref: {described.ref}")
        print(f"Name: {described.name}")
        print(f"Version: {described.version or '-'}")
        print(f"Description: {described.description}")
        if described.homepage:
            print(f"Homepage: {described.homepage}")
        return 0

    print(f"Ref: {installed.key}")
    print(f"Name: {installed.manifest.name}")
    print(f"Version: {installed.package.version}")
    print(f"Description: {installed.manifest.description}")
    print(f"Active: {installed.active}")
    print(f"Install Path: {installed.install_path}")
    if installed.package.homepage:
        print(f"Homepage: {installed.package.homepage}")
    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    manager = _manager(args)
    if not manager.activate(args.name):
        print(f"Error: Skill '{args.name}' not found", file=sys.stderr)
        return 1
    print(f"✓ activated {args.name}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    manager = _manager(args)
    if not manager.uninstall(args.name):
        print(f"Error: Skill '{args.name}' is not installed", file=sys.stderr)
        return 1
    print(f"✓ uninstalled {args.name}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    is_valid, issues = validate_skill_structure(args.path)
    if not is_valid:
        print(f"✗ Invalid skill at {args.path}")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    manifest = SkillManifest.from_file(Path(args.path) / "SKILL.md")
    print(f"✓ Valid skill at {args.path}")
    print(f"  Name: {manifest.name}")
    print(f"  Description: {manifest.description}")
    print(f"  Version: {manifest.version}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
