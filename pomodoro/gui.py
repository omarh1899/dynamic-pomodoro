import sys
import threading

# --- Try to import customtkinter for modern dark UI ---
try:
    import customtkinter as ctk
    CUSTOMTKINTER_AVAILABLE = True
except ImportError:
    CUSTOMTKINTER_AVAILABLE = False

if CUSTOMTKINTER_AVAILABLE:
    import tkinter as tk
    from tkinter import StringVar, IntVar, BooleanVar
else:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import StringVar, IntVar, BooleanVar

from pomodoro.engine import PomodoroEngine, TimerState, recalculate_breaks

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

# --- Modern CustomTkinter GUI ---
if CUSTOMTKINTER_AVAILABLE:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    class PomodoroGUI:
        def __init__(self, root, self_test=False):
            self.root = root
            self.root.title("⚡ DYNAMIC POMODORO")
            # MANDATORY: geometry and minsize per remediation rules
            self.root.geometry("780x620")
            self.root.minsize(760, 560)
            self.root.resizable(True, True)
            self.root.configure(bg=SLATE_BG)
            self.self_test = self_test

            # --- Engine & Storage ---
            self.engine = PomodoroEngine()
            self.storage = _get_session_storage()()

            # --- State Vars ---
            self.state_var = StringVar(value=str(self.engine.state))
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

            # --- Layout using responsive grid ---
            self.root.grid_rowconfigure(0, weight=0)  # header
            self.root.grid_rowconfigure(1, weight=1)  # timer card
            self.root.grid_rowconfigure(2, weight=0)  # duration controls
            self.root.grid_rowconfigure(3, weight=0)  # controls
            self.root.grid_rowconfigure(4, weight=0)  # footer
            self.root.grid_columnconfigure(0, weight=1)

            self._build_header()
            self._build_timer_card()
            self._build_duration_controls()
            self._build_controls()
            self._build_footer()

            self._bind_events()

            self._update_break_labels()
            self._update_footer()
            self._update_state_badge()
            self._update_timer_display()
            self._schedule_tick()

        def _build_header(self):
            header = ctk.CTkFrame(self.root, fg_color=SLATE_BG, corner_radius=0, height=29)
            header.grid(row=0, column=0, sticky="ew", padx=0, pady=(18, 8))
            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0)
            header.grid_columnconfigure(2, weight=0)
            # Title
            title = ctk.CTkLabel(header, text="⚡ DYNAMIC POMODORO", font=("Segoe UI", 14, "bold"), text_color=WHITE)
            title.grid(row=0, column=0, sticky="w", padx=(24, 10), pady=0)
            # Always on Top
            self.always_on_top_chk = ctk.CTkCheckBox(
                header, text="Always on Top", variable=self.always_on_top_var, command=self._toggle_always_on_top,
                font=("Segoe UI", 10), text_color=WHITE, fg_color=GRAY,
                hover_color=NEON_CYAN, border_color=SLATE_BG, border_width=1)
            self.always_on_top_chk.grid(row=0, column=2, sticky="e", padx=(10, 24), pady=0)
            # State badge
            self.state_badge = ctk.CTkLabel(header, text="", font=("Segoe UI", 11, "bold"),
                                            fg_color=GRAY, text_color=SLATE_BG,
                                            corner_radius=12, width=110, height=28)
            self.state_badge.grid(row=0, column=1, sticky="e", padx=(0, 0), pady=0)

        def _build_timer_card(self):
            card = ctk.CTkFrame(self.root, fg_color=CARD_BG, corner_radius=18, height=196)
            card.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 8))
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(0, weight=1)
            # Timer with circular progress
            self.timer_canvas = ctk.CTkCanvas(card, width=180, height=180, bg=CARD_BG, highlightthickness=0)
            self.timer_canvas.grid(row=0, column=0, pady=(16, 0), sticky="n")
            self.timer_label = ctk.CTkLabel(
                master=card,
                textvariable=self.timer_var,
                font=("Consolas", 48, "bold"),
                text_color=NEON_CYAN,
                fg_color="transparent"
            )
            # Place at absolute center of canvas in card
            self.timer_label.place(in_=self.timer_canvas, relx=0.5, rely=0.5, anchor="center")
            self._timer_card = card

        def _draw_progress(self):
            self.timer_canvas.delete("all")
            total = self.engine.focus_seconds
            if str(self.engine.state) in ("SHORT_BREAK", "LONG_BREAK"):
                total = self.engine.long_break_seconds if str(self.engine.state) == "LONG_BREAK" else self.engine.short_break_seconds
            if str(self.engine.state) == "OVERTIME":
                color = AMBER
                percent = 1.0
            elif str(self.engine.state) == "PAUSED":
                color = WHITE
                percent = 1.0
            else:
                color = NEON_CYAN if str(self.engine.state) == "FOCUS" else EMERALD
                percent = min(1.0, max(0.0, self.engine.remaining_seconds / total if total else 0))
            # Draw background circle
            self.timer_canvas.create_oval(10, 10, 170, 170, outline=DARK_GRAY, width=14)
            # Draw arc
            if percent > 0:
                self.timer_canvas.create_arc(10, 10, 170, 170, start=90, extent=-360*percent, style="arc", outline=color, width=14, capstyle="round")
            if str(self.engine.state) == "OVERTIME":
                self.timer_canvas.create_oval(10, 10, 170, 170, outline=AMBER, width=14)

        def _build_duration_controls(self):
            frame = ctk.CTkFrame(self.root, fg_color=CARD_BG, corner_radius=12, height=110)
            frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8))
            frame.grid_rowconfigure(0, weight=0)
            frame.grid_rowconfigure(1, weight=1)
            frame.grid_rowconfigure(2, weight=0)
            frame.grid_columnconfigure(0, weight=0)
            frame.grid_columnconfigure(1, weight=1)
            frame.grid_columnconfigure(2, weight=0)
            # Label
            label = ctk.CTkLabel(frame, text="Focus Duration", font=("Segoe UI", 12, "bold"), text_color=WHITE)
            label.grid(row=0, column=0, sticky="w", padx=(12, 4), pady=(10, 2), columnspan=3)
            # Modern pill slider with spin buttons, filling all available grid width
            self.minus_btn = ctk.CTkButton(frame, text="-", width=44, height=38, font=("Segoe UI", 16, "bold"), fg_color=DARK_GRAY, text_color=WHITE, hover_color=GRAY, corner_radius=6, command=lambda: self._set_focus_duration(self.focus_minutes_var.get()-1))
            self.minus_btn.grid(row=1, column=0, padx=(12, 4), pady=(4, 4), sticky="ew", ipadx=4)
            self.slider = ctk.CTkSlider(
                frame, from_=1, to=120, number_of_steps=119,
                variable=self.focus_minutes_var, command=self._on_focus_slider,
                fg_color=SLATE_BG, progress_color=NEON_CYAN, button_color=NEON_CYAN, button_hover_color=EMERALD,
                width=460, height=14  # modern pill shape
            )
            self.slider.grid(row=1, column=1, sticky="ew", padx=(4, 4), pady=(4, 4))
            self.plus_btn = ctk.CTkButton(frame, text="+", width=44, height=38, font=("Segoe UI", 16, "bold"), fg_color=DARK_GRAY, text_color=WHITE, hover_color=GRAY, corner_radius=6, command=lambda: self._set_focus_duration(self.focus_minutes_var.get()+1))
            self.plus_btn.grid(row=1, column=2, padx=(4, 12), pady=(4, 4), sticky="ew", ipadx=4)
            # Break preview row (padded for clarity and non-overlap)
            self.short_break_label = ctk.CTkLabel(
                frame, text="", font=("Segoe UI", 10, "bold"), text_color="#7ceed6",  # high-contrast mint-blue
            )
            self.short_break_label.grid(row=2, column=0, sticky="w", padx=(12, 4), pady=(0, 10), columnspan=2)
            self.long_break_label = ctk.CTkLabel(
                frame, text="", font=("Segoe UI", 10, "bold"), text_color="#30adf0",  # high-contrast blue
            )
            self.long_break_label.grid(row=2, column=2, sticky="e", padx=(4, 12), pady=(0, 10))

        def _build_controls(self):
            frame = ctk.CTkFrame(self.root, fg_color=SLATE_BG, corner_radius=0, height=136)
            frame.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 8))
            for i in range(6):
                frame.grid_columnconfigure(i, weight=1, uniform="ctrl")
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_rowconfigure(1, weight=1)
            # Row 0: Start, Pause, Reset (spread across, plenty of width/padding)
            self.start_btn = ctk.CTkButton(frame, text="▶ Start", command=self._on_start, fg_color=NEON_CYAN, text_color=SLATE_BG, hover_color=EMERALD, font=("Segoe UI", 13, "bold"), corner_radius=8, height=53, width=200)
            self.start_btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=26, ipady=4)
            self.pause_btn = ctk.CTkButton(frame, text="⏸ Pause", command=self._on_pause, fg_color=CARD_BG, text_color=WHITE, hover_color=NEON_CYAN, font=("Segoe UI", 13, "bold"), corner_radius=8, height=53, width=200)
            self.pause_btn.grid(row=0, column=2, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=26, ipady=4)
            self.reset_btn = ctk.CTkButton(frame, text="↺ Reset", command=self._on_reset, fg_color=CARD_BG, text_color=WHITE, hover_color=NEON_CYAN, font=("Segoe UI", 13, "bold"), corner_radius=8, height=53, width=200)
            self.reset_btn.grid(row=0, column=4, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=26, ipady=4)
            # Row 1: Overtime, Complete Focus
            self.overtime_btn = ctk.CTkButton(frame, text="+5m Flow Overtime", command=self._on_overtime, fg_color=AMBER, text_color=SLATE_BG, hover_color="#fbbf24", font=("Segoe UI", 13, "bold"), corner_radius=8, height=53, width=260)
            self.overtime_btn.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 10), ipadx=26, ipady=4)
            self.complete_btn = ctk.CTkButton(frame, text="⏭ Complete Focus -> Break", command=self._on_complete, fg_color=EMERALD, text_color=SLATE_BG, hover_color="#34d399", font=("Segoe UI", 13, "bold"), corner_radius=8, height=53, width=270)
            self.complete_btn.grid(row=1, column=3, columnspan=3, sticky="ew", padx=8, pady=(6, 10), ipadx=26, ipady=4)

        def _build_footer(self):
            frame = ctk.CTkFrame(self.root, fg_color=SLATE_BG, corner_radius=0, height=21)
            frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(12, 8))
            frame.grid_columnconfigure(0, weight=1)
            self.footer_label = ctk.CTkLabel(
                frame,
                text="",
                font=("Segoe UI", 10, "bold"),
                text_color=GRAY,
                anchor="w"
            )
            self.footer_label.grid(row=0, column=0, sticky="w", padx=(8, 0))

        def _bind_events(self):
            self.focus_minutes_var.trace_add("write", self._on_focus_var_changed)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        def _toggle_always_on_top(self):
            try:
                self.root.wm_attributes("-topmost", self.always_on_top_var.get())
            except Exception:
                pass

        def _on_focus_slider(self, val):
            try:
                minutes = int(float(val))
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
            # Improve contrast on both
            self.short_break_label.configure(
                text=f"Short Break: {format_time(short_secs)}",
                text_color="#7ceed6",
            )
            self.long_break_label.configure(
                text=f"Long Break: {format_time(long_secs)}",
                text_color="#30adf0",
            )

        def _update_state_badge(self):
            raw_state = getattr(self.engine.state, "value", str(self.engine.state))
            state = raw_state.replace("TimerState.", "")
            color = STATE_COLORS.get(state, WHITE)
            label = STATE_LABELS.get(state, state)
            self.state_badge.configure(text=label, fg_color=color, text_color=SLATE_BG if color != WHITE else CARD_BG)
            # Timer color
            if state == "FOCUS":
                self.timer_label.configure(text_color=NEON_CYAN)
            elif state == "OVERTIME":
                self.timer_label.configure(text_color=AMBER)
            elif state in ("SHORT_BREAK", "LONG_BREAK"):
                self.timer_label.configure(text_color=EMERALD)
            elif state == "PAUSED":
                self.timer_label.configure(text_color=WHITE)
            else:
                self.timer_label.configure(text_color=GRAY)
            self._draw_progress()

        def _update_timer_display(self):
            state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
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
            self.footer_label.configure(
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
            prev_state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
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
            state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
            if state in ("FOCUS", "OVERTIME", "SHORT_BREAK", "LONG_BREAK"):
                try:
                    prev_rem = self.engine.remaining_seconds
                    prev_state = state
                    new_state = self.engine.tick(1)
                    new_state_str = getattr(new_state, "value", str(new_state)).replace("TimerState.", "")
                    self._update_timer_display()
                    if prev_state in ("FOCUS", "OVERTIME") and new_state_str in ("SHORT_BREAK", "LONG_BREAK"):
                        focus_mins = self.engine.focus_seconds / 60
                        overtime_mins = self.engine.overtime_seconds / 60
                        self.storage.record_session(focus_mins, overtime_mins)
                        self._update_footer()
                    elif prev_state in ("SHORT_BREAK", "LONG_BREAK") and new_state_str == "IDLE":
                        self._update_footer()
                except Exception:
                    pass

        # --- Self-test logic ---
        def _self_test(self):
            breaks = self.engine.set_focus_duration(50)
            assert breaks["short_break_seconds"] == 600, f"short_break_seconds={breaks['short_break_seconds']}"
            assert breaks["long_break_seconds"] == 1800, f"long_break_seconds={breaks['long_break_seconds']}"
            print("GUI_SELF_TEST_OK")
            self.root.after(100, self.root.destroy)

    def run_gui(self_test: bool = False) -> int:
        try:
            root = ctk.CTk()
        except Exception as e:
            if self_test:
                # fallback to logic-only self test
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

# --- Fallback: Tkinter/ttk version (if customtkinter unavailable) ---
else:
    class PomodoroGUI:
        def __init__(self, root, self_test=False):
            self.root = root
            self.root.title("⚡ DYNAMIC POMODORO")
            self.root.configure(bg=SLATE_BG)
            # MANDATORY: geometry and minsize per remediation rules
            self.root.geometry("780x620")
            self.root.minsize(760, 560)
            self.root.resizable(True, True)
            self.self_test = self_test

            self.engine = PomodoroEngine()
            self.storage = _get_session_storage()()

            self.state_var = StringVar(value=str(self.engine.state))
            self.timer_var = StringVar(value=format_time(self.engine.remaining_seconds))
            self.focus_minutes_var = IntVar(value=int(round(self.engine.focus_seconds / 60)))
            self.short_break_var = StringVar()
            self.long_break_var = StringVar()
            self.always_on_top_var = BooleanVar(value=False)

            self.completed_sessions_var = IntVar(value=0)
            self.total_focus_var = StringVar(value="0")
            self.total_overtime_var = StringVar(value="0")
            self.streak_var = IntVar(value=0)

            self._setup_styles()

            # Responsive grid window
            self.root.rowconfigure(0, weight=0)
            self.root.rowconfigure(1, weight=1)
            self.root.rowconfigure(2, weight=0)
            self.root.rowconfigure(3, weight=0)
            self.root.rowconfigure(4, weight=0)
            self.root.columnconfigure(0, weight=1)

            self._build_header()
            self._build_timer_card()
            self._build_duration_controls()
            self._build_controls()
            self._build_footer()

            self._bind_events()
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
            style.configure("Header.TLabel", background=SLATE_BG, foreground=WHITE, font=("Segoe UI", 14, "bold"))
            style.configure("StateBadge.TLabel", background=GRAY, foreground=SLATE_BG, font=("Segoe UI", 11, "bold"))
            style.configure("Timer.TLabel", background=CARD_BG, foreground=NEON_CYAN, font=("Consolas", 48, "bold"))
            style.configure("BreakPreview.TLabel", background=CARD_BG, foreground="#31a5c1", font=("Segoe UI", 10, "bold"))
            style.configure("Footer.TLabel", background=SLATE_BG, foreground=GRAY, font=("Segoe UI", 10))
            style.configure("TButton", font=("Segoe UI", 13, "bold"), padding=8)
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
            header = ttk.Frame(self.root, style="TFrame", height=29)
            header.grid(row=0, column=0, sticky="ew", pady=(18, 8))
            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0)
            header.grid_columnconfigure(2, weight=0)
            title = ttk.Label(header, text="⚡ DYNAMIC POMODORO", style="Header.TLabel")
            title.grid(row=0, column=0, sticky="w", padx=(24, 10))
            self.always_on_top_chk = ttk.Checkbutton(header, text="Always on Top", variable=self.always_on_top_var, command=self._toggle_always_on_top, style="TCheckbutton")
            self.always_on_top_chk.grid(row=0, column=2, sticky="e", padx=(10, 24))
            self.state_badge = ttk.Label(header, text="", style="StateBadge.TLabel")
            self.state_badge.grid(row=0, column=1, sticky="e", padx=(0, 0), ipadx=8, ipady=2)

        def _build_timer_card(self):
            card = ttk.Frame(self.root, style="Card.TFrame", height=196)
            card.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 8))
            card.grid_columnconfigure(0, weight=1)
            self.timer_canvas = tk.Canvas(card, width=180, height=180, bg=CARD_BG, highlightthickness=0, bd=0)
            self.timer_canvas.grid(row=0, column=0, pady=(16, 0), sticky="n")
            self.timer_label = ttk.Label(card, textvariable=self.timer_var, style="Timer.TLabel", anchor="center", background=CARD_BG)
            self.timer_label.place(in_=self.timer_canvas, relx=0.5, rely=0.5, anchor="center")
            self._timer_card = card

        def _draw_progress(self):
            self.timer_canvas.delete("all")
            total = self.engine.focus_seconds
            if str(self.engine.state) in ("SHORT_BREAK", "LONG_BREAK"):
                total = self.engine.long_break_seconds if str(self.engine.state) == "LONG_BREAK" else self.engine.short_break_seconds
            if str(self.engine.state) == "OVERTIME":
                color = AMBER
                percent = 1.0
            elif str(self.engine.state) == "PAUSED":
                color = WHITE
                percent = 1.0
            else:
                color = NEON_CYAN if str(self.engine.state) == "FOCUS" else EMERALD
                percent = min(1.0, max(0.0, self.engine.remaining_seconds / total if total else 0))
            self.timer_canvas.create_oval(10, 10, 170, 170, outline=DARK_GRAY, width=14)
            if percent > 0:
                self.timer_canvas.create_arc(10, 10, 170, 170, start=90, extent=-360*percent, style="arc", outline=color, width=14)
            if str(self.engine.state) == "OVERTIME":
                self.timer_canvas.create_oval(10, 10, 170, 170, outline=AMBER, width=14)

        def _build_duration_controls(self):
            frame = ttk.Labelframe(self.root, text="Focus Duration", style="Card.TLabelframe", height=110)
            frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8), ipadx=8, ipady=4)
            frame.columnconfigure(0, weight=0)
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(2, weight=0)
            self.minus_btn = tk.Button(frame, text="-", width=3, font=("Segoe UI", 14, "bold"),
                                      bg=DARK_GRAY, fg=WHITE, bd=0, relief="flat", highlightthickness=0,
                                      activebackground=GRAY, activeforeground=WHITE,
                                      command=lambda: self._set_focus_duration(self.focus_minutes_var.get()-1))
            self.minus_btn.grid(row=0, column=0, padx=(12, 4), pady=(8, 4), sticky="ew")
            self.slider = tk.Scale(
                frame, from_=1, to=120, orient="horizontal",
                variable=self.focus_minutes_var, command=self._on_focus_slider,
                bg=CARD_BG, fg=WHITE, troughcolor=SLATE_BG, activebackground=NEON_CYAN,
                highlightthickness=0, bd=0, relief="flat", sliderrelief="flat",
                showvalue=False, length=460, width=14,
            )
            self.slider.grid(row=0, column=1, sticky="ew", padx=(4, 4), pady=(8, 4))
            self.plus_btn = tk.Button(frame, text="+", width=3, font=("Segoe UI", 14, "bold"),
                                     bg=DARK_GRAY, fg=WHITE, bd=0, relief="flat", highlightthickness=0,
                                     activebackground=GRAY, activeforeground=WHITE,
                                     command=lambda: self._set_focus_duration(self.focus_minutes_var.get()+1))
            self.plus_btn.grid(row=0, column=2, padx=(4, 12), pady=(8, 4), sticky="ew")
            self.short_break_label = ttk.Label(frame, text="", style="BreakPreview.TLabel", foreground="#75f9e6")
            self.short_break_label.grid(row=1, column=0, sticky="w", padx=(12, 4), pady=(0, 8), columnspan=2)
            self.long_break_label = ttk.Label(frame, text="", style="BreakPreview.TLabel", foreground="#30adf0")
            self.long_break_label.grid(row=1, column=2, sticky="e", padx=(4, 12), pady=(0, 8))

        def _build_controls(self):
            frame = ttk.Frame(self.root, style="TFrame", height=136)
            frame.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 8))
            for i in range(6):
                frame.columnconfigure(i, weight=1, uniform="ctrl")
            # Row 0: Start, Pause, Reset
            self.start_btn = ttk.Button(frame, text="▶ Start", command=self._on_start, style="Accent.TButton")
            self.start_btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=25, ipady=4)
            self.pause_btn = ttk.Button(frame, text="⏸ Pause", command=self._on_pause)
            self.pause_btn.grid(row=0, column=2, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=25, ipady=4)
            self.reset_btn = ttk.Button(frame, text="↺ Reset", command=self._on_reset)
            self.reset_btn.grid(row=0, column=4, columnspan=2, sticky="ew", padx=8, pady=(8, 6), ipadx=25, ipady=4)
            self.overtime_btn = ttk.Button(frame, text="+5m Flow Overtime", command=self._on_overtime, style="Amber.TButton")
            self.overtime_btn.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 10), ipadx=25, ipady=4)
            self.complete_btn = ttk.Button(frame, text="⏭ Complete Focus -> Break", command=self._on_complete, style="Emerald.TButton")
            self.complete_btn.grid(row=1, column=3, columnspan=3, sticky="ew", padx=8, pady=(6, 10), ipadx=25, ipady=4)

        def _build_footer(self):
            frame = ttk.Frame(self.root, style="TFrame", height=21)
            frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(12, 8))
            frame.columnconfigure(0, weight=1)
            self.footer_label = ttk.Label(
                frame,
                text="",
                style="Footer.TLabel",
                anchor="w"
            )
            self.footer_label.grid(row=0, column=0, sticky="w", padx=(8, 0))

        def _bind_events(self):
            self.focus_minutes_var.trace_add("write", self._on_focus_var_changed)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        def _toggle_always_on_top(self):
            try:
                self.root.attributes("-topmost", self.always_on_top_var.get())
            except Exception:
                pass

        def _on_focus_slider(self, val):
            try:
                minutes = int(float(val))
            except Exception:
                minutes = self.focus_minutes_var.get()
            self.focus_minutes_var.set(minutes)
            self._set_focus_duration(minutes)

        def _on_focus_var_changed(self, *_):
            minutes = self.focus_minutes_var.get()
            self._set_focus_duration(minutes)

        def _set_focus_duration(self, minutes):
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
            self.short_break_label.config(text=f"Short Break: {format_time(short_secs)}", foreground="#75f9e6")
            self.long_break_label.config(text=f"Long Break: {format_time(long_secs)}", foreground="#30adf0")

        def _update_state_badge(self):
            raw_state = getattr(self.engine.state, "value", str(self.engine.state))
            state = raw_state.replace("TimerState.", "")
            color = STATE_COLORS.get(state, WHITE)
            label = STATE_LABELS.get(state, state)
            self.state_badge.config(text=label, background=color, foreground=SLATE_BG if color != WHITE else CARD_BG)
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
            self._draw_progress()

        def _update_timer_display(self):
            state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
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
            prev_state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
            rem = self.engine.complete_focus()
            self._update_state_badge()
            self._update_timer_display()
            if prev_state in ("FOCUS", "OVERTIME"):
                focus_mins = self.engine.focus_seconds / 60
                overtime_mins = self.engine.overtime_seconds / 60
                self.storage.record_session(focus_mins, overtime_mins)
                self._update_footer()

        def _on_close(self):
            self.root.destroy()

        def _schedule_tick(self):
            if not self.self_test:
                self._tick()
                self.root.after(1000, self._schedule_tick)

        def _tick(self):
            state = getattr(self.engine.state, "value", str(self.engine.state)).replace("TimerState.", "")
            if state in ("FOCUS", "OVERTIME", "SHORT_BREAK", "LONG_BREAK"):
                try:
                    prev_rem = self.engine.remaining_seconds
                    prev_state = state
                    new_state = self.engine.tick(1)
                    new_state_str = getattr(new_state, "value", str(new_state)).replace("TimerState.", "")
                    self._update_timer_display()
                    if prev_state in ("FOCUS", "OVERTIME") and new_state_str in ("SHORT_BREAK", "LONG_BREAK"):
                        focus_mins = self.engine.focus_seconds / 60
                        overtime_mins = self.engine.overtime_seconds / 60
                        self.storage.record_session(focus_mins, overtime_mins)
                        self._update_footer()
                    elif prev_state in ("SHORT_BREAK", "LONG_BREAK") and new_state_str == "IDLE":
                        self._update_footer()
                except Exception:
                    pass

        def _self_test(self):
            breaks = self.engine.set_focus_duration(50)
            assert breaks["short_break_seconds"] == 600, f"short_break_seconds={breaks['short_break_seconds']}"
            assert breaks["long_break_seconds"] == 1800, f"long_break_seconds={breaks['long_break_seconds']}"
            print("GUI_SELF_TEST_OK")
            self.root.after(100, self.root.destroy)

    def run_gui(self_test: bool = False) -> int:
        try:
            root = tk.Tk()
        except Exception as e:
            if self_test:
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
