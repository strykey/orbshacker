"""Unified entry point; imports interactive functionality only when
requested.
"""

import sys


def main(argv=None):
    """Dispatch a subcommand or open the original interactive menu."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "verify":
        from .quest_runner import RunnerBusyError
        from .quest_verify import main as verify

        try:
            return verify(args[1:])
        except RunnerBusyError as exc:
            print(f"Cannot start: {exc}", file=sys.stderr)
            return 2
    if args and args[0] == "auto":
        from .quest_runner import RunnerBusyError
        from .quest_runner import main as auto

        try:
            return auto(args[1:])
        except RunnerBusyError as exc:
            print(f"Cannot start: {exc}", file=sys.stderr)
            return 2
    if args and args[0] == "fetch":
        from .quest_fetch import main as fetch

        return fetch(args[1:])
    if args and args[0] == "intake":
        from .quest_input import main as intake

        return intake(args[1:])
    if args and args[0] in ("--help", "-h"):
        print(
            "Usage: python -m orbshacker "
            "[fetch|intake|auto|verify|menu] [options]"
        )
        print(
            "  auto    Match current quests; "
            "--execute starts matching desktop processes"
        )
        print(
            "  verify  Test candidates against server progress "
            "(--help for options)"
        )
        print("  fetch   Display quests or export JSON (--help for options)")
        print(
            "  intake  Validate exported JSON without execution "
            "(--help for options)"
        )
        print("  menu    Open the original interactive menu (default)")
        return 0
    if args and args != ["menu"]:
        print(
            "Unknown command. Use python -m orbshacker --help", file=sys.stderr
        )
        return 2
    from .main import main as menu

    return menu()
