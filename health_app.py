import tkinter as tk
from tkinter import messagebox, ttk
import time
import sys
import argparse
from pathlib import Path


class HealthApp:
    def __init__(self, root, start_hidden=False):
        self.root = root
        self.start_hidden = start_hidden
        self.root.title("Wellness Reminder")
        self.root.geometry("520x460")
        self.root.configure(bg="#0f172a")
        self.running = False
        self.timer_id = None
        self.water_limit = 0
        self.stand_limit = 0
        self.last_water_reminder = 0.0
        self.last_stand_reminder = 0.0
        self.status_var = tk.StringVar(value="Ready")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Command-q>", self.quit_app_event)
        self.root.bind("<Control-q>", self.quit_app_event)
        self.register_reopen_handler()
        self.apply_window_icon()

        self.build_ui()
        self.fit_window_to_content()
        if self.start_hidden:
            self.root.withdraw()
        self.root.after(250, self.start_reminders)

    def resource_path(self, relative_path):
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base_path / relative_path

    def apply_window_icon(self):
        icon_path = self.resource_path("assets/app_icon.png")
        if not icon_path.exists():
            return

        try:
            icon_image = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, icon_image)
            self.root._icon_image = icon_image
        except tk.TclError:
            pass

    def register_reopen_handler(self):
        if sys.platform != "darwin":
            return

        try:
            self.root.createcommand("tk::mac::ReopenApplication", self.on_reopen_application)
        except tk.TclError:
            pass

    def on_reopen_application(self):
        self.show_main_window()

    def show_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.after_idle(self.root.focus_force)

    def fit_window_to_content(self):
        self.root.update_idletasks()
        width = max(520, self.root.winfo_reqwidth())
        height = max(460, self.root.winfo_reqheight())
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)

    def validate_numeric_input(self, proposed_value):
        return proposed_value.isdigit() or proposed_value == ""

    def build_ui(self):
        card = tk.Frame(self.root, bg="#e2ecf9", padx=24, pady=20)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        entry_style = ttk.Style(self.root)
        if "clam" in entry_style.theme_names():
            entry_style.theme_use("clam")
        entry_style.configure(
            "Reminder.TEntry",
            font=("Avenir Next", 13),
            foreground="#f8fafc",
            fieldbackground="#1f2937",
            padding=(12, 8, 12, 8),
            borderwidth=1,
            relief="flat",
        )
        entry_style.configure(
            "Start.TButton",
            font=("Avenir Next", 12, "bold"),
            padding=(18, 10),
            borderwidth=1,
            relief="solid",
        )
        entry_style.map(
            "Start.TButton",
            background=[("disabled", "#99f6e4"), ("active", "#0f766e"), ("!disabled", "#14b8a6")],
            foreground=[("disabled", "#334155"), ("active", "#ecfeff"), ("!disabled", "#0f172a")],
        )
        entry_style.configure(
            "Stop.TButton",
            font=("Avenir Next", 12, "bold"),
            padding=(22, 10),
            borderwidth=1,
            relief="solid",
        )
        entry_style.map(
            "Stop.TButton",
            background=[("disabled", "#cbd5e1"), ("active", "#ea580c"), ("!disabled", "#f97316")],
            foreground=[("disabled", "#475569"), ("!disabled", "#ffffff")],
        )

        tk.Label(
            card,
            text="Wellness Reminder",
            bg="#e2ecf9",
            fg="#0f172a",
            font=("Avenir Next", 24, "bold"),
        ).pack(anchor="w")

        tk.Label(
            card,
            text="Stay focused. Stay hydrated. Move often.",
            bg="#e2ecf9",
            fg="#334155",
            font=("Avenir Next", 12),
        ).pack(anchor="w", pady=(4, 18))

        tk.Label(
            card,
            text="Water Interval (mins)",
            bg="#e2ecf9",
            fg="#1e293b",
            font=("Avenir Next", 12, "bold"),
        ).pack(anchor="w")

        numeric_validate = (self.root.register(self.validate_numeric_input), "%P")

        self.water_entry = ttk.Entry(
            card,
            style="Reminder.TEntry",
            validate="key",
            validatecommand=numeric_validate,
        )
        self.water_entry.insert(0, "30")
        self.water_entry.pack(fill="x", pady=(6, 14))

        tk.Label(
            card,
            text="Stand Up Interval (mins)",
            bg="#e2ecf9",
            fg="#1e293b",
            font=("Avenir Next", 12, "bold"),
        ).pack(anchor="w")

        self.stand_entry = ttk.Entry(
            card,
            style="Reminder.TEntry",
            validate="key",
            validatecommand=numeric_validate,
        )
        self.stand_entry.insert(0, "20")
        self.stand_entry.pack(fill="x", pady=(6, 16))

        controls = tk.Frame(card, bg="#e2ecf9")
        controls.pack(fill="x", pady=(6, 6))

        self.start_btn = ttk.Button(
            controls,
            text="Start Reminders",
            command=self.start_reminders,
            style="Start.TButton",
            cursor="hand2",
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = ttk.Button(
            controls,
            text="Stop",
            command=self.stop_reminders,
            style="Stop.TButton",
            cursor="hand2",
            state="disabled",
        )
        self.stop_btn.pack(side="left")

        status_bar = tk.Frame(card, bg="#d0deee", height=34)
        status_bar.pack(fill="x", pady=(14, 0))
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg="#d0deee",
            fg="#0f172a",
            font=("Avenir Next", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=7)

    def start_reminders(self):
        if self.running:
            return

        try:
            water_minutes = int(self.water_entry.get())
            stand_minutes = int(self.stand_entry.get())
            if water_minutes <= 0 or stand_minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Enter positive whole numbers for both intervals.",
                parent=self.root,
            )
            return

        self.water_limit = water_minutes * 60
        self.stand_limit = stand_minutes * 60
        now = time.time()
        self.last_water_reminder = now
        self.last_stand_reminder = now

        self.running = True
        self.start_btn.config(
            text="Running...",
            state="disabled",
        )
        self.stop_btn.config(
            state="normal",
        )
        self.status_var.set("Reminders running")
        self.schedule_next_check()

    def stop_reminders(self):
        self.running = False
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.start_btn.config(
            text="Start Reminders",
            state="normal",
        )
        self.stop_btn.config(
            state="disabled",
        )
        self.status_var.set("Paused")

    def schedule_next_check(self):
        if self.running:
            self.timer_id = self.root.after(1000, self.run_reminders)

    def run_reminders(self):
        if not self.running:
            return

        now = time.time()

        if now - self.last_water_reminder >= self.water_limit:
            self.show_blocking_popup(
                "STAY HYDRATED!",
                "Time to drink water!",
                "Keep your energy up.",
            )
            self.last_water_reminder = now

        if now - self.last_stand_reminder >= self.stand_limit:
            self.show_blocking_popup(
                "TIME TO MOVE!",
                "Stand up and stretch.",
                "A short walk resets your focus.",
            )
            self.last_stand_reminder = now

        self.schedule_next_check()

    def show_blocking_popup(self, title, headline, message):
        popup = tk.Toplevel(self.root)
        popup.title("Reminder")
        popup.geometry("620x300")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        popup.attributes("-topmost", True)

        bg = "#f3f8ff"
        popup.configure(bg=bg)

        panel = tk.Frame(popup, bg=bg, highlightbackground="#cbd5e1", highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            panel,
            text=title,
            bg=bg,
            fg="#0f172a",
            font=("Avenir Next", 34, "bold"),
        ).pack(pady=(18, 4))

        tk.Label(
            panel,
            text=headline,
            bg=bg,
            fg="#0f172a",
            font=("Avenir Next", 22, "bold"),
        ).pack(pady=(0, 18))

        tk.Label(
            panel,
            text=message,
            bg=bg,
            fg="#334155",
            font=("Avenir Next", 17),
        ).pack(pady=(0, 24))

        def close_popup():
            popup.destroy()

        tk.Button(
            panel,
            text="OK, I Will Do It",
            command=close_popup,
            padx=30,
            pady=10,
            font=("Avenir Next", 14, "bold"),
            cursor="hand2",
        ).pack(pady=(0, 14))

        popup.protocol("WM_DELETE_WINDOW", close_popup)
        self.center_popup(popup)
        self.root.wait_window(popup)

    def center_popup(self, popup):
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        if self.root.winfo_viewable():
            x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        else:
            x = (popup.winfo_screenwidth() - width) // 2
            y = (popup.winfo_screenheight() - height) // 2
        popup.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    def on_close(self):
        self.status_var.set("Running in background" if self.running else "Paused in background")
        self.root.withdraw()

    def quit_app_event(self, _event=None):
        self.quit_app()

    def quit_app(self):
        self.stop_reminders()
        self.root.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--background", action="store_true")
    args, _ = parser.parse_known_args()

    root = tk.Tk()
    app = HealthApp(root, start_hidden=args.background)
    root.mainloop()