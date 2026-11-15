import sys
import threading
import time
import customtkinter as ctk
from pomodoro.engine import PomodoroEngine, TimerState
from pomodoro.storage import SessionStorage

# --- THEME COLORS ---
SLATE_BG = "#181f2a"
SLATE_DARK = "#141925"
SLATE_LIGHT = "#232c3d"
NEON_CYAN = "#00ffe7"
EMERALD = "#2ee59d"
PINK = "#ff3cac"
YELLOW = "#ffe066"
ORANGE = "#ffb347"
RED = "#ff4e4e"
WHITE = "#f3f3f3"
GRAY = "#a0a0a0"

BADGE_COLORS = {
    "IDLE": SLATE_LIGHT,
    "FOCUS": NEON_CYAN,
    "OVERTIME": PINK,
    "SHORT BREAK": EMERALD,
    "LONG BREAK": ORANGE,
    "PAUSED": YELLOW,
}

STATE_LABELS = {
    "IDLE": "IDLE",
    "FOCUS": "FOCUS",
    "OVERTIME": "OVERTIME",
    "SHORT_BREAK": "SHORT BREAK",
    "LONG_BREAK": "LONG BREAK",
    "PAUSED": "PAUSED",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def format_time(secs):
    m, s = divmod(int(secs), 60)
    return f"{m:02}:{s:02}"

class PomodoroGUI:
    def __init__(self, root, self_test=False):
        self.root = root
        self.self_test = self_test
        self.engine = PomodoroEngine()
        self.storage = SessionStorage()
        self._timer_running = False
        self._timer_thread = None
        self._stop_event = threading.Event()
        self._last_tick = time.time()
        self._build_ui()
        self._update_state_badge()
        self._update_timer_label()
        self._draw_progress()
        if self.self_test:
            self.root.after(500, self._self_test_exit)

    def _self_test_exit(self):
        print("GUI_SELF_TEST_OK")
        self.root.destroy()

    def _build_ui(self):
        self.root.title("⚡ DYNAMIC POMODORO")
        self.root.geometry("780x620")
        self.root.minsize(740, 580)
        self.root.resizable(True, True)
        self.root.configure(bg=SLATE_BG)

        # --- HEADER ---
        header = ctk.CTkFrame(self.root, fg_color=SLATE_DARK, height=54)
        header.pack(fill="x", side="top")
        header.grid_propagate(False)
        title = ctk.CTkLabel(header, text="⚡ DYNAMIC POMODORO", font=("Segoe UI", 14, "bold"), text_color=NEON_CYAN)
        title.grid(row=0, column=0, padx=24, pady=14, sticky="w")
        self.state_badge = ctk.CTkLabel(header, text="", font=("Segoe UI", 12, "bold"), fg_color=SLATE_LIGHT, text_color=WHITE, corner_radius=10, width=120, height=32)
        self.state_badge.grid(row=0, column=1, padx=18, pady=10, sticky="e")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        # --- MAIN CARD ---
        card = ctk.CTkFrame(self.root, fg_color=SLATE_LIGHT, corner_radius=18, width=350, height=270)
        card.place(relx=0.5, rely=0.19, anchor="n")
        self.card = card

        # Timer Canvas
        self.timer_canvas = ctk.CTkCanvas(card, width=180, height=180, bg=SLATE_LIGHT, highlightthickness=0)
        self.timer_canvas.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        # Timer Label (centered over canvas)
        self.timer_label = ctk.CTkLabel(card, text="25:00", font=("Segoe UI", 38, "bold"), text_color=WHITE, fg_color="transparent")
        self.timer_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- FOCUS DURATION SLIDER ---
        slider_frame = ctk.CTkFrame(self.root, fg_color="transparent", width=440, height=75)
        slider_frame.place(relx=0.5, rely=0.57, anchor="n")
        slider_label = ctk.CTkLabel(slider_frame, text="Focus Duration (minutes)", font=("Segoe UI", 12, "bold"), text_color=GRAY)
        slider_label.pack(anchor="w", padx=8, pady=(2, 0))
        self.focus_slider = ctk.CTkSlider(
            slider_frame,
            from_=10,
            to=120,
            number_of_steps=110,
            command=self._on_focus_slider,
            fg_color=SLATE_BG,
            progress_color=NEON_CYAN,
            button_color=NEON_CYAN,
            button_hover_color=EMERALD,
            height=18,
        )
        self.focus_slider.set(self.engine.focus_seconds // 60)
        self.focus_value_label = ctk.CTkLabel(slider_frame, text=f"{int(self.engine.focus_seconds // 60)} min", font=("Segoe UI", 11), text_color=WHITE)
        self.focus_value_label.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=2)

        # --- CONTROLS ---
        self._build_controls()

        # --- STATS ---
        stats_frame = ctk.CTkFrame(self.root, fg_color=SLATE_DARK, corner_radius=12, width=680, height=56)
        stats_frame.place(relx=0.5, rely=0.96, anchor="s")
        self.stats_label = ctk.CTkLabel(stats_frame, text="", font=("Segoe UI", 12), text_color=GRAY)
        self.stats_label.place(relx=0.5, rely=0.5, anchor="center")
        self._update_stats()

    def _build_controls(self):
        frame = ctk.CTkFrame(self.root, fg_color="transparent", width=680, height=110)
        frame.place(relx=0.5, rely=0.71, anchor="n")
        for i in range(6):
            frame.grid_columnconfigure(i, weight=1, uniform="ctrl")
        # Row 0: Start, Pause, Reset
        self.start_btn = ctk.CTkButton(frame, text="▶ Start", font=("Segoe UI", 13, "bold"), fg_color=NEON_CYAN, text_color=SLATE_BG, command=self._on_start)
        self.start_btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        self.pause_btn = ctk.CTkButton(frame, text="⏸ Pause", font=("Segoe UI", 13, "bold"), fg_color=YELLOW, text_color=SLATE_BG, command=self._on_pause)
        self.pause_btn.grid(row=0, column=2, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        self.reset_btn = ctk.CTkButton(frame, text="↺ Reset", font=("Segoe UI", 13, "bold"), fg_color=SLATE_LIGHT, text_color=WHITE, command=self._on_reset)
        self.reset_btn.grid(row=0, column=4, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        # Row 1: +5m Overtime, Complete Focus
        self.overtime_btn = ctk.CTkButton(frame, text="+5m Flow Overtime", font=("Segoe UI", 13, "bold"), fg_color=PINK, text_color=WHITE, command=self._on_overtime)
        self.overtime_btn.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 10))
        self.complete_btn = ctk.CTkButton(frame, text="⏭ Complete Focus -> Break", font=("Segoe UI", 13, "bold"), fg_color=EMERALD, text_color=SLATE_BG, command=self._on_complete)
        self.complete_btn.grid(row=1, column=3, columnspan=3, sticky="ew", padx=8, pady=(6, 10))

    def _on_focus_slider(self, val):
        val = int(float(val))
        self.focus_value_label.configure(text=f"{val} min")
        self.engine.set_focus_duration(val)
        self._update_timer_label()
        self._draw_progress()
        self._update_stats()

    def _on_start(self):
        self.engine.start()
        self._update_state_badge()
        self._start_timer()

    def _on_pause(self):
        self.engine.pause()
        self._update_state_badge()
        self._stop_timer()

    def _on_reset(self):
        self.engine.reset()
        self._update_state_badge()
        self._update_timer_label()
        self._draw_progress()
        self._stop_timer()

    def _on_overtime(self):
        try:
            self.engine.add_overtime(5)
        except Exception:
            pass
        self._update_state_badge()
        self._update_timer_label()
        self._draw_progress()

    def _on_complete(self):
        self.engine.complete_focus()
        self._update_state_badge()
        self._update_timer_label()
        self._draw_progress()
        self._update_stats()

    def _start_timer(self):
        if not self._timer_running:
            self._timer_running = True
            self._stop_event.clear()
            self._last_tick = time.time()
            self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
            self._timer_thread.start()

    def _stop_timer(self):
        self._timer_running = False
        self._stop_event.set()

    def _timer_loop(self):
        while self._timer_running and not self._stop_event.is_set():
            now = time.time()
            elapsed = now - self._last_tick
            self._last_tick = now
            if self.engine.state in ("FOCUS", "OVERTIME", "SHORT_BREAK", "LONG_BREAK"):
                try:
                    self.engine.tick(int(elapsed))
                except Exception:
                    pass
                self._update_timer_label()
                self._draw_progress()
                self._update_state_badge()
                if self.engine.state == "IDLE":
                    self._stop_timer()
                    self._update_stats()
            time.sleep(1)
        self._timer_running = False

    def _update_state_badge(self):
        raw_state = getattr(self.engine.state, "value", str(self.engine.state))
        state = raw_state.replace("TimerState.", "").replace("_", " ").upper()
        # Map to pretty label
        pretty = STATE_LABELS.get(state, state)
        color = BADGE_COLORS.get(pretty, SLATE_LIGHT)
        self.state_badge.configure(text=pretty, fg_color=color, text_color=SLATE_BG if pretty in ("FOCUS", "SHORT BREAK", "LONG BREAK") else WHITE)

    def _update_timer_label(self):
        if self.engine.state == "OVERTIME":
            t = self.engine.overtime_seconds
            self.timer_label.configure(text=f"+{format_time(t)}", text_color=PINK)
        elif self.engine.state in ("SHORT_BREAK", "LONG_BREAK", "SHORT BREAK", "LONG BREAK"):
            t = self.engine.remaining_seconds
            self.timer_label.configure(text=format_time(t), text_color=EMERALD if "LONG" not in self.engine.state else ORANGE)
        else:
            t = self.engine.remaining_seconds
            self.timer_label.configure(text=format_time(t), text_color=WHITE)

    def _draw_progress(self):
        self.timer_canvas.delete("all")
        # Draw background circle
        self.timer_canvas.create_oval(10, 10, 170, 170, outline=SLATE_BG, width=14)
        # Progress arc
        if self.engine.state == "FOCUS":
            total = self.engine.focus_seconds
            remain = self.engine.remaining_seconds
            percent = max(0.0, min(1.0, 1 - remain / total)) if total > 0 else 0
            color = NEON_CYAN
        elif self.engine.state == "OVERTIME":
            percent = 1.0
            color = PINK
        elif self.engine.state in ("SHORT_BREAK", "SHORT BREAK"):
            total = self.engine.short_break_seconds
            remain = self.engine.remaining_seconds
            percent = max(0.0, min(1.0, 1 - remain / total)) if total > 0 else 0
            color = EMERALD
        elif self.engine.state in ("LONG_BREAK", "LONG BREAK"):
            total = self.engine.long_break_seconds
            remain = self.engine.remaining_seconds
            percent = max(0.0, min(1.0, 1 - remain / total)) if total > 0 else 0
            color = ORANGE
        else:
            percent = 0.0
            color = NEON_CYAN
        # Draw arc (no capstyle!)
        if percent > 0:
            self.timer_canvas.create_arc(10, 10, 170, 170, start=90, extent=-360*percent, style="arc", outline=color, width=14)
        # Overtime highlight
        if self.engine.state == "OVERTIME":
            self.timer_canvas.create_oval(24, 24, 156, 156, outline=PINK, width=3)

    def _update_stats(self):
        stats = self.storage.load()
        txt = (
            f"Sessions: {stats.get('completed_sessions', 0)}   "
            f"Total Focus: {stats.get('total_focus_minutes', 0.0):.1f} min   "
            f"Total Overtime: {stats.get('total_overtime_minutes', 0.0):.1f} min   "
            f"Streak: {stats.get('streak', 0)}"
        )
        self.stats_label.configure(text=txt)

def run_gui(self_test=False):
    root = ctk.CTk()
    gui = PomodoroGUI(root, self_test=self_test)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0
