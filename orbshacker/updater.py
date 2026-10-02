"""
updater.py – Auto-update from GitHub Releases.

Only runs when the app is a compiled executable (sys.frozen).
Compares the current VERSION against the latest GitHub Release tag.
If a newer version exists, downloads the .exe asset and replaces itself.
"""
# pyright: reportUnusedFunction=false

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

import requests
from packaging.version import InvalidVersion, Version

from . import config, ui


class ReleaseAsset(TypedDict):
    name: str
    browser_download_url: str


class GitHubRelease(TypedDict, total=False):
    tag_name: str
    assets: list[ReleaseAsset]


def _cleanup_old_exe(old_exe: Path) -> None:
    """Delete a leftover backup executable if it exists."""
    if old_exe.exists():
        try:
            old_exe.unlink()
        except Exception:  # noqa: BLE001, S110
            pass


def _schedule_delete(path: Path) -> None:
    """Delete a file shortly after the updater restarts the app."""
    if not path.exists():
        return

    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".cmd", mode="w", encoding="utf-8"
        ) as script_file:
            script_path = Path(script_file.name)
            script_file.write(
                "@echo off\r\n"
                f'set "TARGET={path}"\r\n'
                ":loop\r\n"
                'del /f /q "%TARGET%" >nul 2>&1\r\n'
                'if exist "%TARGET%" (\r\n'
                "  timeout /t 1 /nobreak >nul\r\n"
                "  goto loop\r\n"
                ")\r\n"
                'del /f /q "%~f0" >nul 2>&1\r\n'
            )

        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=0x08000000,
        )
    except Exception:  # noqa: BLE001
        _cleanup_old_exe(path)


def is_frozen() -> bool:
    """Return True if running as a compiled executable (e.g. PyInstaller)."""
    return getattr(sys, "frozen", False)


def _parse_version(tag: str) -> Version:
    """Parse a version tag like 'v2.1.0' or '2.1.0' into a Version object."""
    return Version(tag.lstrip("v"))


def _get_latest_release() -> GitHubRelease | None:
    """Fetch the latest release info from the GitHub API.
    Returns dict with 'tag_name' and 'assets' or None on failure.
    """
    url = f"https://api.github.com/repos/{config.GITHUB_REPO_OWNER}/{config.GITHUB_REPO_NAME}/releases/latest"
    try:
        resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


def _find_exe_asset(assets: list[ReleaseAsset]) -> ReleaseAsset | None:
    """Find the .exe download asset from a release."""
    for asset in assets:
        name = asset.get("name", "")
        if name.lower().endswith(".exe"):
            return asset
    return None


def _download_file(url: str, dest: Path) -> None:
    """Download a file from url to dest path."""
    resp = requests.get(url, stream=True, timeout=config.REQUEST_TIMEOUT_LONG)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(8192):
            if chunk:
                f.write(chunk)


def _replace_exe(new_exe: Path) -> None:
    """Replace the currently running .exe with the new one.

    On Windows we can't overwrite a running file, so we:
    1. Rename current exe to .old
    2. Move new exe into place
    3. Launch new exe
    4. Exit current process
    """
    current_exe = Path(sys.executable)
    old_exe = current_exe.with_suffix(".old")

    # Clean up any previous .old file
    if old_exe.exists():
        try:
            os.remove(old_exe)
        except Exception:  # noqa: BLE001, S110
            pass

    try:
        os.rename(current_exe, old_exe)
        new_exe.rename(current_exe)
        ui.print_color("[UPDATE] Updated to new version!", ui.Colors.GREEN, bold=True)
        ui.print_color("[UPDATE] Restarting...", ui.Colors.CYAN)

        # Launch the new exe and exit
        os.startfile(str(current_exe))
        _schedule_delete(old_exe)
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        # Try to restore original
        if old_exe.exists() and not current_exe.exists():
            os.rename(old_exe, current_exe)
        ui.print_color(f"[UPDATE] Failed to apply update: {e}", ui.Colors.RED)


def auto_update() -> None:
    """Check for updates and auto-update if a new release is available.

    Only runs when the app is a compiled executable.
    Skips silently when running from source.
    """
    if not is_frozen():
        return  # Running from source – skip update entirely

    _cleanup_old_exe(Path(sys.executable).with_suffix(".old"))

    try:
        ui.loading_animation("Checking for updates", 1.2)
    except Exception:  # noqa: BLE001, S110
        pass

    # 1. Fetch latest release
    release = _get_latest_release()
    if not release:
        return

    # 2. Compare versions
    tag = release.get("tag_name", "")
    try:
        remote_version = _parse_version(tag)
        local_version = _parse_version(config.VERSION)
    except InvalidVersion:
        return

    if remote_version <= local_version:
        ui.print_color(
            f"[UPDATE] You're up to date (v{config.VERSION})", ui.Colors.CYAN
        )
        return

    # 3. Find exe download
    asset = _find_exe_asset(release.get("assets", []))
    if not asset:
        ui.print_color(
            f"[UPDATE] v{tag} available but no .exe found in release", ui.Colors.YELLOW
        )
        ui.print_color(
            f"[UPDATE] Download manually: {config.REPO_URL}/releases/latest",
            ui.Colors.GRAY,
        )
        return

    # 4. Download + replace
    ui.print_color(
        f"[UPDATE] New version available: {config.VERSION} → {tag}",
        ui.Colors.GREEN,
        bold=True,
    )
    try:
        ui.loading_animation(f"Downloading {asset['name']}", 2.0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".exe") as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            _download_file(asset["browser_download_url"], tmp_path)
            _replace_exe(tmp_path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:  # noqa: BLE001, S110
                    pass
    except Exception as e:  # noqa: BLE001
        ui.print_color(f"[UPDATE] Download failed: {e}", ui.Colors.YELLOW)
        ui.print_color(
            f"[UPDATE] Download manually: {config.REPO_URL}/releases/latest",
            ui.Colors.GRAY,
        )


# ── Kept for tests (pure functions) ───────────────────────────────────────────


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
