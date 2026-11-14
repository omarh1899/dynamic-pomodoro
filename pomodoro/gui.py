import tkinter as tk
from tkinter import ttk
from tkinter import StringVar, IntVar, BooleanVar
from pomodoro.engine import PomodoroEngine, TimerState, recalculate_breaks

import sys
import threading

# --- Color Palette ---
SLATE_BG = "#0f172a"
CARD_BG = "#1e293b"
NEON_CYAN = "#38bdf8"
EMERALD = "#10b981"
AMBER = "#f59e0b"
WHITE = "#f8fafc"
GRAY = "#64748b"
DARK_GRAY = "#334155"

STATE_COLORS = {
    "IDLE": GRAY,
    "FOCUS": NEON_CYAN,
    "OVERTIME": AMBER,
    "SHORT_BREAK": EMERALD,
    "LONG_BREAK": EMERALD,
    "PAUSED": WHITE,
}

STATE_LABELS = {
    "IDLE": "IDLE",
    "FOCUS": "FOCUS",
    "OVERTIME": "OVERTIME",
    "SHORT_BREAK": "SHORT BREAK",
    "LONG_BREAK": "LONG BREAK",
    "PAUSED": "PAUSED",
}

def format_time(secs, show_plus=False):
    sign = ""
    if show_plus and secs > 0:
        sign = "+"
    mins = abs(secs) // 60
    s = abs(secs) % 60
    return f"{sign}{mins:02}:{s:02}"

class _DummySessionStorage:
    def __init__(self, path="session_stats.json"):
        self._stats = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0,
        }
    def load(self):
        return dict(self._stats)
    def record_session(self, focus_minutes, overtime_minutes):
        self._stats["completed_sessions"] += 1
        self._stats["total_focus_minutes"] += focus_minutes
        self._stats["total_overtime_minutes"] += overtime_minutes
        self._stats["streak"] += 1
        return dict(self._stats)
    def reset_stats(self):
        self._stats = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0,
        }
        return dict(self._stats)

def _get_session_storage():
    try:
        from pomodoro.storage import SessionStorage
        return SessionStorage
    except ImportError:
        return _DummySessionStorage

class PomodoroGUI:
    def __init__(self, root, self_test=False):
        self.root = root
        self.root.title("⚡ DYNAMIC POMODORO // CLUSTER EDITION")
        self.root.configure(bg=SLATE_BG)
        self.root.minsize(480, 420)
        self.root.geometry("540x480")
        self.root.resizable(False, False)
        self.self_test = self_test

        # --- Engine & Storage ---
        self.engine = PomodoroEngine()
        self.storage = _get_session_storage()()

        # --- State Vars ---
        self.state_var = StringVar(value=self.engine.state)
        self.timer_var = StringVar(value=format_time(self.engine.remaining_seconds))
        self.focus_minutes_var = IntVar(value=int(round(self.engine.focus_seconds / 60)))
        self.short_break_var = StringVar()
        self.long_break_var = StringVar()
        self.always_on_top_var = BooleanVar(value=False)

        # Footer stats
        self.completed_sessions_var = IntVar(value=0)
        self.total_focus_var = StringVar(value="0")
        self.total_overtime_var = StringVar(value="0")
        self.streak_var = IntVar(value=0)

        # --- Style ---
        self._setup_styles()

        # --- Layout ---
        self._build_header()
        self._build_timer_card()
        self._build_duration_controls()
        self._build_controls()
        self._build_footer()

        # --- Bindings ---
        self._bind_events()

        # --- Initial update ---
        self._update_break_labels()
        self._update_footer()
        self._update_state_badge()
        self._update_timer_display()
        self._schedule_tick()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=SLATE_BG)
        style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        style.configure("Header.TLabel", background=SLATE_BG, foreground=WHITE, font=("Segoe UI", 16, "bold"))
        style.configure("StateBadge.TLabel", background=CARD_BG, foreground=WHITE, font=("Segoe UI", 10, "bold"))
        style.configure("Timer.TLabel", background=CARD_BG, foreground=NEON_CYAN, font=("Consolas", 48, "bold"))
        style.configure("BreakPreview.TLabel", background=CARD_BG, foreground=EMERALD, font=("Segoe UI", 10))
        style.configure("Footer.TLabel", background=SLATE_BG, foreground=GRAY, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=6)
        style.map("TButton",
            background=[("active", DARK_GRAY), ("!active", CARD_BG)],
            foreground=[("active", NEON_CYAN), ("!active", WHITE)]
        )
        style.configure("Accent.TButton", background=NEON_CYAN, foreground=SLATE_BG)
        style.map("Accent.TButton",
            background=[("active", EMERALD), ("!active", NEON_CYAN)],
            foreground=[("active", SLATE_BG), ("!active", SLATE_BG)]
        )
        style.configure("Amber.TButton", background=AMBER, foreground=SLATE_BG)
        style.map("Amber.TButton",
            background=[("active", "#fbbf24"), ("!active", AMBER)],
            foreground=[("active", SLATE_BG), ("!active", SLATE_BG)]
        )
        style.configure("Emerald.TButton", background=EMERALD, foreground=SLATE_BG)
        style.map("Emerald.TButton",
            background=[("active", "#34d399"), ("!active", EMERALD)],
            foreground=[("active", SLATE_BG), ("!active", SLATE_BG)]
        )
        style.configure("Card.TLabelframe", background=CARD_BG, foreground=WHITE)
        style.configure("Card.TLabelframe.Label", background=CARD_BG, foreground=WHITE)
        style.configure("TCheckbutton", background=SLATE_BG, foreground=WHITE, font=("Segoe UI", 10))

    def _build_header(self):
        header = ttk.Frame(self.root, style="TFrame")
        header.pack(fill="x", pady=(18, 8))
        title = ttk.Label(header, text="⚡ DYNAMIC POMODORO // CLUSTER EDITION", style="Header.TLabel")
        title.pack(side="left", padx=(24, 8))
        self.state_badge = ttk.Label(header, text="", style="StateBadge.TLabel")
        self.state_badge.pack(side="left", padx=(8, 0), ipadx=8, ipady=2)
        # Always on top
        self.always_on_top_chk = ttk.Checkbutton(header, text="Always on Top", variable=self.always_on_top_var, command=self._toggle_always_on_top, style="TCheckbutton")
        self.always_on_top_chk.pack(side="right", padx=(0, 24))

    def _build_timer_card(self):
        card = ttk.Frame(self.root, style="Card.TFrame")
        card.pack(fill="x", padx=32, pady=(0, 8))
        self.timer_label = ttk.Label(card, textvariable=self.timer_var, style="Timer.TLabel", anchor="center")
        self.timer_label.pack(pady=(18, 10), fill="x")
        # For focus/overtime/break color change
        self._timer_card = card

    def _build_duration_controls(self):
        frame = ttk.Labelframe(self.root, text="Focus Duration", style="Card.TLabelframe")
        frame.pack(fill="x", padx=32, pady=(0, 8), ipadx=8, ipady=4)
        # Slider
        slider = ttk.Scale(frame, from_=1, to=120, orient="horizontal", variable=self.focus_minutes_var, command=self._on_focus_slider)
        slider.grid(row=0, column=0, sticky="ew", padx=(12, 4), pady=8)
        frame.columnconfigure(0, weight=1)
        # Spinbox
        self.spinbox = tk.Spinbox(frame, from_=1, to=120, width=4, textvariable=self.focus_minutes_var, font=("Segoe UI", 11), command=self._on_focus_spinbox, bg=CARD_BG, fg=WHITE, insertbackground=WHITE, highlightbackground=CARD_BG, relief="flat", justify="center")
        self.spinbox.grid(row=0, column=1, padx=(4, 12), pady=8)
        # Short/long break preview
        self.short_break_label = ttk.Label(frame, text="", style="BreakPreview.TLabel")
        self.short_break_label.grid(row=1, column=0, sticky="w", padx=(12, 4), pady=(0, 8))
        self.long_break_label = ttk.Label(frame, text="", style="BreakPreview.TLabel")
        self.long_break_label.grid(row=1, column=1, sticky="e", padx=(4, 12), pady=(0, 8))

    def _build_controls(self):
        frame = ttk.Frame(self.root, style="TFrame")
        frame.pack(fill="x", padx=32, pady=(0, 8))
        # Start
        self.start_btn = ttk.Button(frame, text="▶ Start", command=self._on_start, style="Accent.TButton")
        self.start_btn.grid(row=0, column=0, padx=4, pady=10, sticky="ew")
        # Pause
        self.pause_btn = ttk.Button(frame, text="⏸ Pause", command=self._on_pause)
        self.pause_btn.grid(row=0, column=1, padx=4, pady=10, sticky="ew")
        # Reset
        self.reset_btn = ttk.Button(frame, text="↺ Reset", command=self._on_reset)
        self.reset_btn.grid(row=0, column=2, padx=4, pady=10, sticky="ew")
        # Overtime
        self.overtime_btn = ttk.Button(frame, text="+5m Flow Overtime", command=self._on_overtime, style="Amber.TButton")
        self.overtime_btn.grid(row=0, column=3, padx=4, pady=10, sticky="ew")
        # Complete
        self.complete_btn = ttk.Button(frame, text="⏭ Complete Focus -> Break", command=self._on_complete, style="Emerald.TButton")
        self.complete_btn.grid(row=0, column=4, padx=4, pady=10, sticky="ew")
        frame.columnconfigure((0, 1, 2, 3, 4), weight=1)

    def _build_footer(self):
        frame = ttk.Frame(self.root, style="TFrame")
        frame.pack(fill="x", side="bottom", padx=16, pady=(12, 8))
        self.footer_label = ttk.Label(
            frame,
            text="",
            style="Footer.TLabel",
            anchor="w"
        )
        self.footer_label.pack(side="left", padx=(8, 0))

    def _bind_events(self):
        self.focus_minutes_var.trace_add("write", self._on_focus_var_changed)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _toggle_always_on_top(self):
        try:
            self.root.attributes("-topmost", self.always_on_top_var.get())
        except Exception:
            pass

    def _on_focus_slider(self, val):
        # Called by slider movement
        try:
            minutes = int(float(val))
        except Exception:
            minutes = self.focus_minutes_var.get()
        self.focus_minutes_var.set(minutes)
        self._set_focus_duration(minutes)

    def _on_focus_spinbox(self):
        try:
            minutes = int(self.spinbox.get())
        except Exception:
            minutes = self.focus_minutes_var.get()
        self.focus_minutes_var.set(minutes)
        self._set_focus_duration(minutes)

    def _on_focus_var_changed(self, *_):
        minutes = self.focus_minutes_var.get()
        self._set_focus_duration(minutes)

    def _set_focus_duration(self, minutes):
        # Clamp
        if minutes < 1:
            minutes = 1
        elif minutes > 120:
            minutes = 120
        self.focus_minutes_var.set(minutes)
        breaks = self.engine.set_focus_duration(minutes)
        self._update_break_labels()
        self._update_timer_display()

    def _update_break_labels(self):
        short_secs = self.engine.short_break_seconds
        long_secs = self.engine.long_break_seconds
        self.short_break_label.config(text=f"Short Break: {format_time(short_secs)}")
        self.long_break_label.config(text=f"Long Break: {format_time(long_secs)}")

    def _update_state_badge(self):
        state = self.engine.state
        color = STATE_COLORS.get(state, WHITE)
        label = STATE_LABELS.get(state, state)
        self.state_badge.config(text=label, background=color, foreground=SLATE_BG if color != WHITE else CARD_BG)
        # Timer color
        if state == "FOCUS":
            self.timer_label.config(foreground=NEON_CYAN)
        elif state == "OVERTIME":
            self.timer_label.config(foreground=AMBER)
        elif state in ("SHORT_BREAK", "LONG_BREAK"):
            self.timer_label.config(foreground=EMERALD)
        elif state == "PAUSED":
            self.timer_label.config(foreground=WHITE)
        else:
            self.timer_label.config(foreground=GRAY)

    def _update_timer_display(self):
        state = self.engine.state
        if state == "OVERTIME":
            self.timer_var.set(format_time(self.engine.overtime_seconds, show_plus=True))
        else:
            self.timer_var.set(format_time(self.engine.remaining_seconds))
        self._update_state_badge()

    def _update_footer(self):
        stats = self.storage.load()
        self.completed_sessions_var.set(stats.get("completed_sessions", 0))
        self.total_focus_var.set(str(int(round(stats.get("total_focus_minutes", 0)))))
        self.total_overtime_var.set(str(int(round(stats.get("total_overtime_minutes", 0)))))
        self.streak_var.set(stats.get("streak", 0))
        self.footer_label.config(
            text=f"Sessions: {self.completed_sessions_var.get()}   "
                 f"Focus: {self.total_focus_var.get()}m   "
                 f"Overtime: {self.total_overtime_var.get()}m   "
                 f"Streak: {self.streak_var.get()}"
        )

    def _on_start(self):
        self.engine.start()
        self._update_state_badge()
        self._update_timer_display()

    def _on_pause(self):
        self.engine.pause()
        self._update_state_badge()
        self._update_timer_display()

    def _on_reset(self):
        self.engine.reset()
        self._update_state_badge()
        self._update_timer_display()

    def _on_overtime(self):
        try:
            self.engine.add_overtime(5.0)
        except Exception:
            pass
        self._update_state_badge()
        self._update_timer_display()

    def _on_complete(self):
        prev_state = self.engine.state
        rem = self.engine.complete_focus()
        self._update_state_badge()
        self._update_timer_display()
        # Only record session if coming from FOCUS or OVERTIME
        if prev_state in ("FOCUS", "OVERTIME"):
            focus_mins = self.engine.focus_seconds / 60
            overtime_mins = self.engine.overtime_seconds / 60
            self.storage.record_session(focus_mins, overtime_mins)
            self._update_footer()

    def _on_close(self):
        self.root.destroy()

    def _schedule_tick(self):
        # Called every 1s
        if not self.self_test:
            self._tick()
            self.root.after(1000, self._schedule_tick)

    def _tick(self):
        state = self.engine.state
        if state in ("FOCUS", "OVERTIME", "SHORT_BREAK", "LONG_BREAK"):
            try:
                prev_rem = self.engine.remaining_seconds
                prev_state = state
                new_state = self.engine.tick(1)
                self._update_timer_display()
                if prev_state in ("FOCUS", "OVERTIME") and new_state in ("SHORT_BREAK", "LONG_BREAK"):
                    # Completed a session, record stats
                    focus_mins = self.engine.focus_seconds / 60
                    overtime_mins = self.engine.overtime_seconds / 60
                    self.storage.record_session(focus_mins, overtime_mins)
                    self._update_footer()
                elif prev_state in ("SHORT_BREAK", "LONG_BREAK") and new_state == "IDLE":
                    self._update_footer()
            except Exception:
                pass

    # --- Self-test logic ---
    def _self_test(self):
        # Test dynamic break recalculation for 50m
        breaks = self.engine.set_focus_duration(50)
        assert breaks["short_break_seconds"] == 600, f"short_break_seconds={breaks['short_break_seconds']}"
        assert breaks["long_break_seconds"] == 1800, f"long_break_seconds={breaks['long_break_seconds']}"
        print("GUI_SELF_TEST_OK")
        self.root.after(100, self.root.destroy)

def run_gui(self_test: bool = False) -> int:
    # If headless, skip GUI and only test engine binding
    try:
        root = tk.Tk()
    except Exception as e:
        if self_test:
            # Headless: test engine binding only
            engine = PomodoroEngine()
            breaks = engine.set_focus_duration(50)
            assert breaks["short_break_seconds"] == 600
            assert breaks["long_break_seconds"] == 1800
            print("GUI_SELF_TEST_OK")
            return 0
        else:
            raise

    gui = PomodoroGUI(root, self_test=self_test)
    if self_test:
        gui._self_test()
        root.mainloop()
        return 0
    else:
        root.mainloop()
        return 0
