import tkinter as tk
from tkinter import messagebox, ttk
import time
import sys
import argparse
import queue
import subprocess
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    import pystray
except ImportError:
    Image = None
    ImageDraw = None
    pystray = None


class HealthApp:
    def __init__(self, root, start_hidden=False, menu_only=False, auto_start=False):
        self.root = root
        self.start_hidden = start_hidden
        self.menu_only = menu_only
        self.tray_icon = None
        self.ui_action_queue = queue.SimpleQueue()
        self.root.title("Wellness Reminder")
        self.root.geometry("520x460")
        self.root.configure(bg="#0f172a")
        self.running = False
        self.timer_id = None
        self.water_limit = 0
        self.stand_limit = 0
        self.stand_break_seconds = 5 * 60
        self.water_due_at = None
        self.stand_due_at = None
        self.stand_break_due_at = None
        self.water_remaining = None
        self.stand_remaining = None
        self.stand_break_remaining = None
        self.status_var = tk.StringVar(value="Ready")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Command-q>", self.quit_app_event)
        self.root.bind("<Control-q>", self.quit_app_event)
        self.configure_macos_presentation()
        self.register_reopen_handler()
        self.apply_window_icon()

        self.build_ui()
        self.fit_window_to_content()
        if self.start_hidden or self.menu_only:
            self.root.withdraw()
        self.root.after(30, self.process_ui_actions)
        if auto_start:
            self.root.after(250, self.start_reminders)
        self.setup_menu_bar_icon()

    def configure_macos_presentation(self):
        if sys.platform != "darwin" or not self.menu_only:
            return

        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            pass

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
        if not self.menu_only:
            self.show_main_window()

    def show_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.after_idle(self.root.focus_force)

    def setup_menu_bar_icon(self):
        if sys.platform != "darwin" or pystray is None or Image is None:
            return

        image = self.load_tray_image()
        if image is None:
            return

        menu_items = []
        if not self.menu_only:
            menu_items.append(pystray.MenuItem("Show Wellness Reminder", self.tray_show_window))

        menu_items.extend(
            [
                pystray.MenuItem("Start Reminders", self.tray_start_reminders, enabled=self.start_enabled),
                pystray.MenuItem("Pause Reminders", self.tray_pause_reminders, enabled=self.pause_enabled),
                pystray.MenuItem("Reset Countdowns", self.tray_reset_countdowns),
                pystray.MenuItem(
                    "Set Water Interval",
                    pystray.Menu(
                        pystray.MenuItem("1 min", lambda icon, item: self.tray_set_interval("water", 1)),
                        pystray.MenuItem("15 mins", lambda icon, item: self.tray_set_interval("water", 15)),
                        pystray.MenuItem("30 mins", lambda icon, item: self.tray_set_interval("water", 30)),
                        pystray.MenuItem("45 mins", lambda icon, item: self.tray_set_interval("water", 45)),
                        pystray.MenuItem("60 mins", lambda icon, item: self.tray_set_interval("water", 60)),
                    ),
                ),
                pystray.MenuItem(self.water_countdown_label, self.tray_noop, enabled=False),
                pystray.MenuItem(
                    "Set Stand Interval",
                    pystray.Menu(
                        pystray.MenuItem("1 min", lambda icon, item: self.tray_set_interval("stand", 1)),
                        pystray.MenuItem("10 mins", lambda icon, item: self.tray_set_interval("stand", 10)),
                        pystray.MenuItem("20 mins", lambda icon, item: self.tray_set_interval("stand", 20)),
                        pystray.MenuItem("30 mins", lambda icon, item: self.tray_set_interval("stand", 30)),
                        pystray.MenuItem("45 mins", lambda icon, item: self.tray_set_interval("stand", 45)),
                    ),
                ),
                pystray.MenuItem(self.stand_countdown_label, self.tray_noop, enabled=False),
                pystray.MenuItem("Quit", self.tray_quit_app),
            ]
        )

        menu = pystray.Menu(*menu_items)
        self.tray_icon = pystray.Icon("wellness_reminder", image, "Wellness Reminder", menu)
        try:
            self.tray_icon.run_detached()
        except Exception as exc:
            self.tray_icon = None
            print(f"Menu bar icon failed to start: {exc}", file=sys.stderr)

    def load_tray_image(self):
        icon_candidates = [
            self.resource_path("assets/menu_bar_icon.png"),
            self.resource_path("assets/menu_bar_icon.jpg"),
            self.resource_path("assets/app_icon.png"),
        ]

        if getattr(sys, "frozen", False):
            bundle_icon = Path(sys.executable).resolve().parent.parent / "Resources" / "AppIcon.icns"
            icon_candidates.append(bundle_icon)

        for icon_path in icon_candidates:
            if not icon_path.exists():
                continue
            try:
                return Image.open(str(icon_path)).convert("RGBA").resize((64, 64), Image.LANCZOS)
            except OSError:
                continue

        if ImageDraw is None:
            return None

        # Use a high-contrast generated icon so the status item is visible.
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(14, 165, 233, 255))
        draw.text((23, 16), "W", fill=(255, 255, 255, 255))
        return image

    def start_enabled(self, _item):
        return not self.running

    def pause_enabled(self, _item):
        return self.running

    def tray_show_window(self, _icon, _item):
        self.enqueue_ui_action("show")

    def tray_start_reminders(self, _icon, _item):
        self.enqueue_ui_action("start")

    def tray_pause_reminders(self, _icon, _item):
        self.enqueue_ui_action("pause")

    def tray_reset_countdowns(self, _icon, _item):
        self.enqueue_ui_action("reset_countdowns")

    def tray_quit_app(self, _icon, _item):
        self.enqueue_ui_action("quit")

    def tray_noop(self, _icon=None, _item=None):
        return

    def tray_set_interval(self, interval_type, minutes):
        self.enqueue_ui_action("set_interval", interval_type, minutes)

    def enqueue_ui_action(self, action, *payload):
        self.ui_action_queue.put((action, payload))

    def process_ui_actions(self):
        while True:
            try:
                action, payload = self.ui_action_queue.get_nowait()
            except queue.Empty:
                break

            if action == "show":
                self.show_main_window()
                continue

            if action == "toggle":
                if self.running:
                    self.stop_reminders()
                else:
                    self.start_reminders()
                continue

            if action == "start":
                self.start_reminders()
                continue

            if action == "pause":
                self.stop_reminders()
                continue

            if action == "reset_countdowns":
                self.reset_countdowns()
                continue

            if action == "quit":
                self.quit_app()
                return

            if action == "set_interval" and len(payload) == 2:
                interval_type, minutes = payload
                self.apply_interval_change(interval_type, minutes)

        self.root.after(30, self.process_ui_actions)

    def refresh_tray_menu(self):
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.update_menu()
        except Exception:
            pass

    def format_duration(self, total_seconds):
        total_seconds = max(0, int(total_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

    def remaining_seconds(self, reminder_type):
        now = time.time()
        if reminder_type == "water":
            due_at = self.water_due_at
            paused_remaining = self.water_remaining
        else:
            due_at = self.stand_due_at
            paused_remaining = self.stand_remaining

        if self.running and due_at is not None:
            return max(0, int(math.ceil(due_at - now)))

        if paused_remaining is not None:
            return max(0, int(paused_remaining))

        return None

    def water_countdown_label(self, _item):
        seconds = self.remaining_seconds("water")
        if seconds is None:
            return "Water in: not started"
        if self.running:
            return f"Water in: {self.format_duration(seconds)}"
        return f"Water paused at: {self.format_duration(seconds)}"

    def stand_countdown_label(self, _item):
        seconds = self.remaining_seconds("stand")
        if seconds is None:
            return "Stand in: not started"
        if self.running and self.stand_break_due_at is not None:
            break_seconds = max(0, int(math.ceil(self.stand_break_due_at - time.time())))
            if break_seconds > 0:
                return f"Stand break: {self.format_duration(break_seconds)}"
        if not self.running and self.stand_break_remaining is not None and self.stand_break_remaining > 0:
            return f"Stand break paused at: {self.format_duration(self.stand_break_remaining)}"
        if self.running:
            return f"Stand in: {self.format_duration(seconds)}"
        return f"Stand paused at: {self.format_duration(seconds)}"

    def apply_interval_change(self, interval_type, minutes):
        try:
            minutes = int(minutes)
            if minutes <= 0:
                return
        except (TypeError, ValueError):
            return

        now = time.time()
        if interval_type == "water":
            self.water_entry.delete(0, tk.END)
            self.water_entry.insert(0, str(minutes))
            self.water_limit = minutes * 60
            if self.running:
                self.water_due_at = now + self.water_limit
                self.water_remaining = self.water_limit
            else:
                self.water_remaining = self.water_limit
            self.status_var.set(f"Water interval set to {minutes} mins")
            self.refresh_tray_menu()
            return

        if interval_type == "stand":
            self.stand_entry.delete(0, tk.END)
            self.stand_entry.insert(0, str(minutes))
            self.stand_limit = minutes * 60
            self.stand_break_due_at = None
            self.stand_break_remaining = None
            if self.running:
                self.stand_due_at = now + self.stand_limit
                self.stand_remaining = self.stand_limit
            else:
                self.stand_remaining = self.stand_limit
            self.status_var.set(f"Stand interval set to {minutes} mins")
            self.refresh_tray_menu()

    def reset_countdowns(self):
        try:
            water_minutes = int(self.water_entry.get())
            stand_minutes = int(self.stand_entry.get())
            if water_minutes <= 0 or stand_minutes <= 0:
                raise ValueError
        except ValueError:
            self.status_var.set("Cannot reset: invalid intervals")
            return

        self.water_limit = water_minutes * 60
        self.stand_limit = stand_minutes * 60
        self.water_remaining = self.water_limit
        self.stand_remaining = self.stand_limit
        self.water_due_at = None
        self.stand_due_at = None
        self.stand_break_due_at = None
        self.stand_break_remaining = None

        if self.running:
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
            self.status_var.set("Countdowns reset and paused")
        else:
            self.status_var.set("Countdowns reset (paused)")

        self.refresh_tray_menu()

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

        if self.water_remaining is None:
            self.water_remaining = self.water_limit
        if self.stand_remaining is None:
            self.stand_remaining = self.stand_limit

        self.water_remaining = max(0, min(int(self.water_remaining), self.water_limit))
        stand_max_remaining = self.stand_limit + self.stand_break_seconds
        self.stand_remaining = max(0, min(int(self.stand_remaining), stand_max_remaining))

        if self.water_remaining == 0:
            self.water_remaining = self.water_limit
        if self.stand_remaining == 0:
            self.stand_remaining = self.stand_limit

        self.water_due_at = now + self.water_remaining
        self.stand_due_at = now + self.stand_remaining
        if self.stand_break_remaining is not None and self.stand_break_remaining > 0:
            self.stand_break_remaining = min(int(self.stand_break_remaining), int(self.stand_remaining))
            self.stand_break_due_at = now + self.stand_break_remaining
        else:
            self.stand_break_due_at = None
            self.stand_break_remaining = None

        self.running = True
        self.start_btn.config(
            text="Running...",
            state="disabled",
        )
        self.stop_btn.config(
            state="normal",
        )
        self.status_var.set("Reminders running")
        self.refresh_tray_menu()
        self.schedule_next_check()

    def stop_reminders(self):
        if self.running:
            now = time.time()
            if self.water_due_at is not None:
                self.water_remaining = max(0, int(math.ceil(self.water_due_at - now)))
            if self.stand_due_at is not None:
                self.stand_remaining = max(0, int(math.ceil(self.stand_due_at - now)))
            if self.stand_break_due_at is not None:
                break_remaining = max(0, int(math.ceil(self.stand_break_due_at - now)))
                self.stand_break_remaining = break_remaining if break_remaining > 0 else None
            else:
                self.stand_break_remaining = None
            self.stand_break_due_at = None

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
        self.refresh_tray_menu()

    def schedule_next_check(self):
        if self.running:
            self.timer_id = self.root.after(1000, self.run_reminders)

    def run_reminders(self):
        if not self.running:
            return

        now = time.time()

        if self.water_due_at is not None and now >= self.water_due_at:
            self.show_blocking_popup(
                "STAY HYDRATED!",
                "Time to drink water!",
                "Keep your energy up.",
            )
            now = time.time()
            self.water_due_at = now + self.water_limit
            self.water_remaining = self.water_limit
        elif self.water_due_at is not None:
            self.water_remaining = max(0, int(math.ceil(self.water_due_at - now)))

        if self.stand_break_due_at is not None:
            if now >= self.stand_break_due_at:
                self.stand_break_due_at = None
                self.stand_break_remaining = None
                self.show_blocking_popup(
                    "BREAK COMPLETE!",
                    "You can sit back down.",
                    "Your next stand reminder will continue from now.",
                )
                now = time.time()
            else:
                self.stand_break_remaining = max(0, int(math.ceil(self.stand_break_due_at - now)))

        if self.stand_due_at is not None and now >= self.stand_due_at:
            self.show_blocking_popup(
                "TIME TO MOVE!",
                "Stand up and stretch.",
                "A short walk resets your focus.",
            )
            now = time.time()
            self.stand_break_due_at = now + self.stand_break_seconds
            self.stand_break_remaining = self.stand_break_seconds
            self.stand_due_at = self.stand_break_due_at + self.stand_limit
            self.stand_remaining = self.stand_break_seconds + self.stand_limit
        elif self.stand_due_at is not None:
            self.stand_remaining = max(0, int(math.ceil(self.stand_due_at - now)))

        self.refresh_tray_menu()

        self.schedule_next_check()

    def show_blocking_popup(self, title, headline, message):
        host_was_hidden, alpha_was_changed = self.prepare_popup_host_window()
        root_is_visible = self.root.winfo_viewable()

        popup = tk.Toplevel(self.root)
        popup.title("Reminder")
        popup.geometry("620x300")
        popup.resizable(False, False)
        if root_is_visible:
            popup.transient(self.root)
        try:
            popup.grab_set()
        except tk.TclError:
            pass
        popup.attributes("-topmost", True)
        popup.lift()
        popup.focus_force()

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
            text="OK",
            command=close_popup,
            padx=30,
            pady=10,
            font=("Avenir Next", 14, "bold"),
            cursor="hand2",
        ).pack(pady=(0, 14))

        popup.protocol("WM_DELETE_WINDOW", close_popup)
        self.center_popup(popup)
        popup.after(40, self.activate_app_window)
        popup.after(60, popup.lift)
        popup.after(80, popup.focus_force)
        self.root.wait_window(popup)
        self.restore_popup_host_window(host_was_hidden, alpha_was_changed)

    def prepare_popup_host_window(self):
        host_was_hidden = not self.root.winfo_viewable()
        alpha_was_changed = False

        if host_was_hidden:
            self.root.deiconify()
            self.root.lift()
            try:
                self.root.attributes("-alpha", 0.0)
                alpha_was_changed = True
            except tk.TclError:
                alpha_was_changed = False

        self.activate_app_window()
        return host_was_hidden, alpha_was_changed

    def restore_popup_host_window(self, host_was_hidden, alpha_was_changed):
        if not host_was_hidden:
            return

        if alpha_was_changed:
            try:
                self.root.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
        self.root.withdraw()

    def activate_app_window(self):
        if sys.platform != "darwin":
            return

        try:
            from AppKit import (
                NSApplication,
                NSRunningApplication,
                NSApplicationActivateAllWindows,
                NSApplicationActivateIgnoringOtherApps,
            )

            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            app = NSRunningApplication.currentApplication()
            app.activateWithOptions_(NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps)
        except Exception:
            try:
                # Keep activation fallback short so popup UI never hangs.
                subprocess.run(
                    ["osascript", "-e", 'tell application "Wellness Reminder" to activate'],
                    check=False,
                    timeout=0.8,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass

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
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.stop_reminders()
        self.root.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--autostart", action="store_true")
    args, _ = parser.parse_known_args()

    root = tk.Tk()
    menu_only_mode = not args.show_gui
    app = HealthApp(
        root,
        start_hidden=args.background or menu_only_mode,
        menu_only=menu_only_mode,
        auto_start=args.autostart,
    )
    root.mainloop()