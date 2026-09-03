"""
faker.py – GameFaker class, manual_mode, and executable launching.

In frozen (.exe) mode:   copies orbshacker.exe itself → GameName.exe (--timer-mode)
In source mode:           copies pythonw.exe → GameName.exe + _orbshacker_timer.pyw
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .path_utils import sanitize_relative_path
from .ui import (
    Colors,
    ask_confirm,
    loading_animation,
    print_boxed_title,
    print_color,
)

# Timer code embedded for source mode – written as a standalone .pyw file
# so that the renamed Python interpreter can run it without any package dependency.
_TIMER_PYW_CODE = """\
import tkinter as tk
import sys
import subprocess
from pathlib import Path

# Baked configurations
AUTO_DELETE = False
AUTO_CLOSE = True
TIMER_MINUTES = 15
STEAM_MANIFEST_PATH = None

class TimerApp:
    def __init__(self, root, minutes=15, title="Timer"):
        root.title(title)
        root.geometry("400x250")
        root.resizable(False, False)
        root.configure(bg="#1a1a1a")
        self.root = root
        self.remaining = minutes * 60

        self.auto_close = tk.BooleanVar(value=AUTO_CLOSE)
        self.auto_close_toggle = tk.Checkbutton(
            root,
            text="Close when timer ends",
            variable=self.auto_close,
            command=self.toggle_auto_close,
            font=("Segoe UI", 10),
            fg="#e0e0e0",
            bg="#1a1a1a",
            activeforeground="#e0e0e0",
            activebackground="#1a1a1a",
            cursor="hand2",
            selectcolor="#1a1a1a",
            bd=1,
        )
        self.auto_close_toggle.pack(pady=(15, 0))

        self.timer_label = tk.Label(
            root,
            text=f"{minutes:02d}:00",
            font=("Consolas", 56, "bold"),
            fg="#e0e0e0",
            bg="#1a1a1a",
        )
        self.timer_label.pack(expand=True)

        self.time_adjust_label = tk.Label(
            root,
            text="Add or reduce time",
            font=("Segoe UI", 9),
            fg="#666666",
            bg="#1a1a1a",
        )
        self.time_adjust_label.pack()

        self.time_adjust_frame = tk.Frame(
            root,
            bg="#1a1a1a",
        )
        self.time_adjust_frame.pack(pady=(2, 10))

        self.minus_button = tk.Button(
            self.time_adjust_frame,
            text="-",
            command=lambda: self.adjust_time(-30),
            font=("Segoe UI", 18, "bold"),
            fg="#e0e0e0",
            bg="#1a1a1a",
            activeforeground="#e0e0e0",
            activebackground="#1a1a1a",
            cursor="hand2",
            width=2,
            height=1,
            padx=0,
            pady=0,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.minus_button.pack(side="left")

        self.time_adjust_label_value = tk.Label(
            self.time_adjust_frame,
            text="30s",
            font=("Segoe UI", 10),
            fg="#e0e0e0",
            bg="#1a1a1a",
            padx=8,
        )
        self.time_adjust_label_value.pack(side="left")

        self.plus_button = tk.Button(
            self.time_adjust_frame,
            text="+",
            command=lambda: self.adjust_time(30),
            font=("Segoe UI", 14, "bold"),
            fg="#e0e0e0",
            bg="#1a1a1a",
            activeforeground="#e0e0e0",
            activebackground="#1a1a1a",
            cursor="hand2",
            width=2,
            height=1,
            padx=0,
            pady=0,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.plus_button.pack(side="left")

        self.status_label = tk.Label(
            root,
            text="Running",
            font=("Segoe UI", 10),
            fg="#666666",
            bg="#1a1a1a",
        )
        self.status_label.pack(side="bottom", pady=(0, 15))

        self.update_time_adjust_buttons()
        self._tick()

    def _tick(self):
        m, s = divmod(self.remaining, 60)
        self.timer_label.config(text=f"{m:02d}:{s:02d}")

        if self.remaining > 0:
            self.remaining -= 1
            self.update_time_adjust_buttons()
            self.root.after(1000, self._tick)
        else:
            self.timer_label.config(text="00:00", fg="#ff6b6b")
            self.status_label.config(text="Complete", fg="#ff6b6b")
            self.update_time_adjust_buttons()
            self.root.update()

            if AUTO_DELETE:
                self.trigger_self_destruction()
            elif self.auto_close.get():
                self.root.destroy()
                sys.exit(0)

    def toggle_auto_close(self) -> None:
        if self.auto_close.get() and self.remaining <= 0:
            self.root.destroy()
            sys.exit(0)
        
    def adjust_time(self, seconds):
        self.remaining = max(0, self.remaining + seconds)

        m, s = divmod(self.remaining, 60)
        self.timer_label.config(text=f"{m:02d}:{s:02d}")

        self.update_time_adjust_buttons()

    def update_time_adjust_buttons(self) -> None:
        minus_state = "disabled" if self.remaining <= 30 else "normal"
        plus_state = "disabled" if self.remaining <= 0 else "normal"

        self.minus_button.config(state=minus_state)
        self.plus_button.config(state=plus_state)

    def trigger_self_destruction(self):
        exe_path = Path(sys.executable)
        script_path = Path(sys.argv[0])
        dir_path = exe_path.parent

        exe_str = str(exe_path).replace("/", "\\\\")
        script_str = str(script_path).replace("/", "\\\\")
        dir_str = str(dir_path).replace("/", "\\\\")

        cmd_parts = [
            "ping 127.0.0.1 -n 3 > nul",
            f'del /f /q "{exe_str}" "{script_str}"'
        ]
        if STEAM_MANIFEST_PATH:
            manifest_str = str(Path(STEAM_MANIFEST_PATH)).replace("/", "\\\\")
            cmd_parts.append(f'del /f /q "{manifest_str}"')
        cmd_parts.append(f'rmdir "{dir_str}"')

        cmd = " && ".join(cmd_parts)
        subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        self.root.destroy()
        sys.exit(0)

root = tk.Tk()
title = sys.argv[1] if len(sys.argv) > 1 else "Timer"
TimerApp(root, TIMER_MINUTES, title)
root.mainloop()
"""


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _find_source_exe() -> Path:
    """Find the executable to copy for fake game processes."""
    if _is_frozen():
        return Path(sys.executable)  # copy ourselves

    # Source mode: prefer the real pythonw.exe from sys.base_prefix to avoid venv launcher stub issues
    base_dir = Path(sys.base_prefix)
    pythonw = base_dir / "pythonw.exe"
    if pythonw.exists():
        return pythonw
    python = base_dir / "python.exe"
    if python.exists():
        return python

    # Fallback to sys.executable's parent
    pythonw_fallback = Path(sys.executable).parent / "pythonw.exe"
    if pythonw_fallback.exists():
        return pythonw_fallback
    return Path(sys.executable)  # fallback to python.exe


class GameFaker:
    def __init__(self):
        self._frozen = _is_frozen()
        self._source_exe = _find_source_exe()
        self.chosen_path = config.CHOSEN_FOLDER
        self._created_files = []
        self._created_dirs = []
        self._processes = []

    def register_created_file(self, path: Path) -> None:
        """Register a file to be deleted on cleanup."""
        self._created_files.append(Path(path))

    def register_parent_dirs(self, path: Path, limit_dir: Path) -> None:
        """Register parent directories of *path* up to *limit_dir* to check for deletion on cleanup."""
        parent = path.parent
        limit_dir_res = limit_dir.resolve()
        while parent.resolve() != limit_dir_res and parent != parent.parent:
            if parent not in self._created_dirs:
                self._created_dirs.append(parent)
            parent = parent.parent

    def copy_exe_to(self, target_path: Path) -> None:
        """Copy the faker executable to *target_path*.

        In source mode, also creates a ``_orbshacker_timer.pyw`` next to
        the target so the renamed Python interpreter can run it.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._source_exe, target_path)
        self.register_created_file(target_path)

        target_path_str = str(target_path).replace("\\", "/")
        if "steamapps/common" in target_path_str:
            parts = target_path_str.split("steamapps/common")
            limit_dir = Path(parts[0] + "steamapps/common")
        else:
            limit_dir = self.chosen_path

        self.register_parent_dirs(target_path, limit_dir)

        target_config = {
            "CHOSEN_FOLDER": str(config.CHOSEN_FOLDER).replace("\\", "/"),
            "AUTO_DELETE": config.AUTO_DELETE,
            "AUTO_CLOSE": config.AUTO_CLOSE,
            "TIMER_MINUTES": config.TIMER_MINUTES,
        }
        manifest_path = getattr(config, "STEAM_MANIFEST_PATH", None)
        if manifest_path:
            target_config["STEAM_MANIFEST_PATH"] = str(manifest_path).replace("\\", "/")

        import json

        if self._frozen:
            try:
                json_data = json.dumps(target_config).encode("utf-8")
                marker = b"__ORBSHACKER_BAKED_CONFIG__"
                with open(target_path, "ab") as f:
                    f.write(marker + json_data + marker)
            except Exception:  # noqa: BLE001, S110
                pass
        else:
            timer_script = target_path.parent / "_orbshacker_timer.pyw"
            if not timer_script.exists():
                code = _TIMER_PYW_CODE
                code = code.replace(
                    "AUTO_DELETE = False", f"AUTO_DELETE = {config.AUTO_DELETE}"
                )
                code = code.replace(
                    "AUTO_CLOSE = True", f"AUTO_CLOSE = {config.AUTO_CLOSE}"
                )
                code = code.replace(
                    "TIMER_MINUTES = 15", f"TIMER_MINUTES = {config.TIMER_MINUTES}"
                )
                if manifest_path:
                    code = code.replace(
                        "STEAM_MANIFEST_PATH = None",
                        f"STEAM_MANIFEST_PATH = {str(manifest_path)!r}",
                    )
                timer_script.write_text(code, encoding="utf-8")
                self.register_created_file(timer_script)

    def create_fake_game(self, exe_name: str) -> Path | None:
        """Create fake game executable under Desktop/<FAKE_EXE_DIR>/."""
        exe_name = sanitize_relative_path(exe_name)
        if not exe_name.lower().endswith(".exe"):
            exe_name += ".exe"
        target_path = self.chosen_path / config.FAKE_EXE_DIR / exe_name
        try:
            loading_animation(f"Creating {exe_name.split('/')[-1]}", 0.8)
            self.copy_exe_to(target_path)
            print_color(f"[OK] Created: {target_path}", Colors.GREEN, bold=True)
            return target_path
        except Exception as e:  # noqa: BLE001
            print_color(
                f"[ERROR] Failed to create executable: {e}", Colors.RED, bold=True
            )
            print_color("[!] Check file permissions or disk space", Colors.YELLOW)
            return None

    def launch_executable(self, exe_path: Path, title: str = "Timer") -> bool:
        """Launch the fake game process in background."""
        try:
            loading_animation("Launching process", 0.8)

            if self._frozen:
                args = [str(exe_path), title]
                env = None
            else:
                timer_script = exe_path.parent / "_orbshacker_timer.pyw"
                args = [str(exe_path), str(timer_script), title]
                env = os.environ.copy()
                base_prefix = Path(sys.base_prefix)
                env["PYTHONHOME"] = str(base_prefix)

                path_parts = [str(base_prefix), env.get("PATH", "")]
                env["PATH"] = os.pathsep.join(part for part in path_parts if part)

            if sys.platform == "win32":
                DETACHED_PROCESS = 0x00000008
                proc = subprocess.Popen(
                    args,
                    env=env,
                    creationflags=DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            else:
                proc = subprocess.Popen(
                    args,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            self._processes.append(proc)

            print_color("[OK] Process launched in background", Colors.GREEN, bold=True)
            print_color(
                "[*] Discord should now detect the game (if Discord is running)",
                Colors.CYAN,
            )
            print_color(
                "[!] IMPORTANT: Discord MUST be running for the spoofing to work",
                Colors.YELLOW,
            )
            print_color(
                "[*] Wait a few seconds for Discord to scan processes", Colors.GRAY
            )
            print_color(
                "[*] TIP: You can run this tool multiple times to emulate multiple games!",
                Colors.MAGENTA,
            )
            return True
        except Exception as e:  # noqa: BLE001
            print_color(f"[!] Failed to auto-launch: {e}", Colors.YELLOW)
            print_color(f"[*] You can manually run: {exe_path}", Colors.CYAN)
            return False

    def cleanup(self) -> None:
        """Clean up all launched processes and created files if AUTO_DELETE is enabled."""
        if not config.AUTO_DELETE:
            return

        print_color(
            "\n[*] AUTO_DELETE enabled. Cleaning up faked processes and files...",
            Colors.CYAN,
        )

        # 1. Terminate all launched processes
        for proc in self._processes:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001, S110
                pass

        # Wait a moment for processes to release file handles
        if self._processes:
            time.sleep(1.0)
            for proc in self._processes:
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001, S110
                    pass

        # 2. Delete all created files
        for file_path in self._created_files:
            deleted = False
            for attempt in range(5):
                try:
                    if file_path.exists():
                        file_path.unlink()
                    deleted = True
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(0.2)
            if not deleted and file_path.exists():
                print_color(
                    f"[!] Failed to delete: {file_path} (file is locked)", Colors.YELLOW
                )

        # 3. Clean up empty parent directories (deepest first)
        sorted_dirs = sorted(
            self._created_dirs, key=lambda p: len(p.parts), reverse=True
        )
        for dir_path in sorted_dirs:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except Exception:  # noqa: BLE001, S110
                pass

        print_color("[OK] Cleanup complete!", Colors.GREEN)


def manual_mode(faker: GameFaker) -> None:
    """Manual mode – user types an exact process name to fake."""
    print_boxed_title("MANUAL MODE", width=50, color=Colors.CYAN)
    print_color("[*] Enter the exact process name Discord expects", Colors.CYAN)
    print_color("[*] Examples:", Colors.GRAY)
    print_color("    • TslGame.exe (PUBG)", Colors.GRAY)
    print_color("    • League of Legends.exe (LoL)", Colors.GRAY)
    print_color("    • Overwatch.exe", Colors.GRAY)
    print_color(
        "[*] Make sure the name matches exactly (case-sensitive on some systems)",
        Colors.GRAY,
    )
    print()

    exe_name = input(
        f"{Colors.BOLD}Executable name{Colors.RESET} (or 'back'): "
    ).strip()
    if not exe_name or exe_name.lower() in ("back", "b"):
        return

    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Executable: {Colors.CYAN}{exe_name}{Colors.RESET}")
    print(
        f"  Path: {Colors.GRAY}{faker.chosen_path / config.FAKE_EXE_DIR / exe_name}{Colors.RESET}"
    )

    if not ask_confirm():
        print_color("\n[!] Operation cancelled", Colors.YELLOW)
        time.sleep(config.SLEEP_SHORT)
        return

    result = faker.create_fake_game(exe_name)
    if result:
        print()
        faker.launch_executable(result)
        print_color("\n[OK] Setup complete!", Colors.GREEN, bold=True)
        print_color(
            "[!] IMPORTANT: Discord MUST be running for the spoofing to work",
            Colors.YELLOW,
        )

    input(f"\n{Colors.GRAY}Press Enter to continue...{Colors.RESET}")
