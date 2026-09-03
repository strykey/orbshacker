"""
timer.py – Fake game process: a simple countdown timer.

When orbshacker copies itself (or pythonw.exe) and renames it to a game's
executable name, the copy runs this timer. Discord sees the process name
and thinks the game is running.
"""

import sys
import tkinter as tk
from orbshacker import config

WINDOW_TITLE     = "Timer"
WINDOW_SIZE      = "400x250"
BG_COLOR         = "#1a1a1a"
TEXT_COLOR        = "#e0e0e0"
ACCENT_COLOR     = "#4a9eff"
SECONDARY_COLOR  = "#666666"
DONE_COLOR       = "#ff6b6b"
TIMER_MINUTES    = 15


class TimerApp:
    def __init__(self, root: tk.Tk, minutes: int = 15):
        self.root: tk.Tk = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        self.remaining = minutes * 60

        self.auto_close = tk.BooleanVar(value=getattr(config, "AUTO_CLOSE", True))
        self.auto_close_toggle = tk.Checkbutton(
            root,
            text="Close when timer ends",
            variable=self.auto_close,
            font=("Segoe UI", 10),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
            activeforeground=TEXT_COLOR,
            activebackground=BG_COLOR,
            selectcolor=BG_COLOR,
        )
        self.auto_close_toggle.pack(pady=(15, 0))

        self.timer_label: tk.Label = tk.Label(
            root, text=f"{minutes:02d}:00",
            font=("Consolas", 56, "bold"), fg=TEXT_COLOR, bg=BG_COLOR,
        )
        self.timer_label.pack(expand=True)

        self.status_label: tk.Label = tk.Label(
            root, text="Running",
            font=("Segoe UI", 10), fg=SECONDARY_COLOR, bg=BG_COLOR,
        )
        self.status_label.pack(side="bottom", pady=20)

        self._tick()

    def _tick(self):
        m, s = divmod(self.remaining, 60)
        self.timer_label.config(text=f"{m:02d}:{s:02d}")
        if self.remaining > 0:
            self.remaining -= 1
            self.root.after(1000, self._tick)
        else:
            self.timer_label.config(text="00:00", fg=DONE_COLOR)
            self.status_label.config(text="Complete", fg=DONE_COLOR)
            self.root.update()
            
            if config.AUTO_DELETE:
                self.trigger_self_destruction()

            # If AUTO_CLOSE is enabled, but AUTO_DELETE is not, close the window and exit
            elif self.auto_close.get():
                self.root.destroy()
                import sys
                sys.exit(0)


    def trigger_self_destruction(self) -> None:
        """Spawn a detached command to delete faked files and directories, and exit."""

        import sys
        import subprocess
        from pathlib import Path

        # Resolve paths
        if getattr(sys, "frozen", False):
            exe_path = Path(sys.executable)
            settings_path = exe_path.parent / "settings.json"
            dir_path = exe_path.parent
        else:
            exe_path = Path(sys.argv[0])
            settings_path = exe_path.parent / "settings.json"
            dir_path = exe_path.parent

        exe_str = str(exe_path).replace("/", "\\")
        settings_str = str(settings_path).replace("/", "\\")
        dir_str = str(dir_path).replace("/", "\\")

        files_to_delete = [exe_str]
        if settings_path.exists():
            files_to_delete.append(settings_str)

        # In dev mode, check if we created _orbshacker_timer.pyw next to script
        if not getattr(sys, "frozen", False):
            timer_script = dir_path / "_orbshacker_timer.pyw"
            if timer_script.exists():
                files_to_delete.append(str(timer_script).replace("/", "\\"))

        # If there's a steam manifest, delete it too
        manifest_path = getattr(config, "STEAM_MANIFEST_PATH", None)
        if manifest_path:
            manifest_str = str(Path(manifest_path)).replace("/", "\\")
            files_to_delete.append(manifest_str)

        files_q = " ".join(f'"{f}"' for f in files_to_delete)
        cmd_parts = [
            "ping 127.0.0.1 -n 3 > nul",
            f'del /f /q {files_q}'
        ]

        # Delete empty parent directory
        cmd_parts.append(f'rmdir "{dir_str}"')

        # Assemble command string
        cmd = " && ".join(cmd_parts)

        # Spawn detached command prompt
        subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

        # Destroy Tkinter window and exit immediately
        self.root.destroy()
        sys.exit(0)


def run_timer(minutes: int = 15) -> None:
    """Entry point for the fake game process."""
    root = tk.Tk()
    TimerApp(root, minutes)
    root.mainloop()
