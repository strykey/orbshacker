import tkinter as tk

WINDOW_TITLE = "Timer"
WINDOW_SIZE = "400x250"
BACKGROUND_COLOR = "#1a1a1a"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#4a9eff"
SECONDARY_COLOR = "#666666"
TIMER_MINUTES = 15


class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND_COLOR)

        self.remaining_seconds = TIMER_MINUTES * 60

        self.build_ui()
        self.update_timer()

    def build_ui(self):
        self.timer_label = tk.Label(
            self.root,
            text="15:00",
            font=("Consolas", 56, "bold"),
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR
        )
        self.timer_label.pack(expand=True)

        self.status_label = tk.Label(
            self.root,
            text="Running",
            font=("Segoe UI", 10),
            fg=SECONDARY_COLOR,
            bg=BACKGROUND_COLOR
        )
        self.status_label.pack(side="bottom", pady=20)

    def update_timer(self):
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.root.after(1000, self.update_timer)
        else:
            self.timer_label.config(text="00:00", fg="#ff6b6b")
            self.status_label.config(text="Complete", fg="#ff6b6b")


if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()
