#!/usr/bin/env python3
"""
Backward-compatible entry point.

Usage:
    python orbshacker.py         (main menu)
    python -m orbshacker         (package-style)

When launched with --timer-mode (by a renamed copy of itself),
it runs the 15-minute timer instead of the main menu.
"""

import os
import sys
from pathlib import Path

# ── Safety: redirect stdio to devnull when running without a console ──────────
# PyInstaller --noconsole (or pythonw) sets sys.stdout/stderr/stdin to None.
# Redirect to devnull so print() / input() don't crash the whole app.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115
if sys.stdin is None:
    sys.stdin = open(os.devnull, "r")  # noqa: SIM115


def is_faked_game() -> bool:
    """Check if the currently running executable/script is a faked game copy."""
    if getattr(sys, "frozen", False):
        name = Path(sys.executable).name.lower()
        return name != "orbshacker.exe"
    else:
        name = Path(sys.argv[0]).name.lower()
        return name not in ("orbshacker.py", "__main__.py") and "pytest" not in name


def show_console() -> None:
    """Allocate and show a Windows console window if running on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes

            # Only allocate a console if we don't have one already
            if not ctypes.windll.kernel32.GetConsoleWindow():
                # Try to attach to parent console first
                if not ctypes.windll.kernel32.AttachConsole(-1):
                    # Otherwise, allocate a new console window
                    ctypes.windll.kernel32.AllocConsole()

                # Reopen standard streams
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115
                sys.stdin = open("CONIN$", "r", encoding="utf-8")  # noqa: SIM115
        except Exception:  # noqa: BLE001, S110
            pass


if __name__ == "__main__":
    if is_faked_game() or "--timer-mode" in sys.argv:
        from orbshacker.timer import run_timer

        try:
            idx = sys.argv.index("--timer-mode")
            minutes = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            from orbshacker import config

            minutes = config.TIMER_MINUTES
        run_timer(minutes)
    else:
        show_console()
        from orbshacker.main import main
        from orbshacker.ui import Colors, print_color

        try:
            main()
        except KeyboardInterrupt:
            print_color("\n\n[!] Interrupted", Colors.YELLOW)
            sys.exit(0)
        except Exception as e:  # noqa: BLE001
            print_color(f"\n[ERROR] Fatal error: {e}", Colors.RED, bold=True)
            import traceback

            traceback.print_exc()
            input("\nPress Enter to exit...")
            sys.exit(1)
