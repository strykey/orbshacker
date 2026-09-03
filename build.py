#!/usr/bin/env python3
"""
build.py – Automates compiling orbshacker.

This script:
1. Resolves the latest version from git tags.
2. Writes the version to orbshacker/_version.py.
3. Invokes PyInstaller with the proper parameters to build a single executable.
"""

import subprocess
import sys
from pathlib import Path

from orbshacker import _version as _build_version


def get_git_version() -> str:
    """Retrieve the latest tag from Git, falling back to '0.0.0'."""
    try:
        res = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
            capture_output=True,
            text=True,
            check=True,
        )
        tag = res.stdout.strip()
        if tag:
            return tag.lstrip("v")
    except Exception:  # noqa: BLE001, S110
        pass
    return getattr(
        _build_version, "VERSION", "0.0.0"
    )  # Fallback to the version in _version.py if git fails


def main():
    # 1. Resolve version
    version = get_git_version()
    print(f"[*] Resolving version from Git: {version}")

    # 2. Write to orbshacker/_version.py
    version_file = Path("orbshacker") / "_version.py"
    print(f"[*] Baking version into: {version_file}")
    version_file.write_text(f'VERSION = "{version}"\n', encoding="utf-8")

    # 3. Find PyInstaller executable in current venv if possible
    pyinstaller_bin = Path(sys.executable).parent / "pyinstaller"
    pyinstaller_exe = pyinstaller_bin.with_suffix(".exe")
    if pyinstaller_exe.exists():
        pyinstaller_cmd = str(pyinstaller_exe)
    elif pyinstaller_bin.exists():
        pyinstaller_cmd = str(pyinstaller_bin)
    else:
        pyinstaller_cmd = "pyinstaller"  # fallback to PATH

    # 4. Build command line
    cmd = [
        pyinstaller_cmd,
        "--onefile",
        "--name",
        "orbshacker",
        "--noconsole",
        "--icon",
        "orbshacker.ico",
        "--add-data",
        "settings.py;.",
        "--collect-all",
        "orbshacker",
        "orbshacker.py",
    ]

    print(f"[*] Executing PyInstaller command:\n    {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\n[OK] Build completed successfully! Check the 'dist' directory.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] PyInstaller execution failed with exit code: {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
