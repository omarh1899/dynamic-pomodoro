# Dynamic Pomodoro

A cyberpunk-inspired Desktop Pomodoro app with dynamic break scaling, "flow state" overtime rewards, a dark neon Tkinter GUI, and CLI tools. Designed with multi-worktree compatibility: all modules precisely specified for parallel, interchangeable implementation.

---

## Features

- **Dynamic Break Scaling**: Changing your focus duration instantly recalculates break lengths using formulas:
  - Short Break: `short_break_seconds = round(focus_seconds * 0.20)`
  - Long Break:  `long_break_seconds  = round(focus_seconds * 0.60)`
  - Each break value is clamped within configurable min/max bounds.

- **Flow-State Overtime Credit**: When you push past your timer (overtime), bonus rest is added to your next break:
  - If entering a **short break**: `bonus_seconds = round(overtime_seconds * 0.25)`
  - If entering a **long break**:  `bonus_seconds = round(overtime_seconds * 0.60)`

- **Deterministic State Machine**: Reliable, unit-testable timer engine (`tick()`-driven) with the following states:
  - `IDLE`, `FOCUS`, `OVERTIME`, `SHORT_BREAK`, `LONG_BREAK`, `PAUSED`

- **Persistent Session Storage**: All-time stats and streak tracked in JSON (`session_stats.json`).

- **CLI & GUI Tools**:
  - Command-line interface for calculations, status, and self-test
  - Desktop Tkinter GUI features focus duration slider, spinner, "+5m Flow Overtime", Always-On-Top toggle, skip/take break, big countdown, and cyberpunk theme

---

## Dynamic Break Scaling

Given a **Focus** duration in minutes:

```
focus_seconds        = round(focus_minutes * 60)
short_break_seconds  = clamp(round(focus_seconds * 0.20), min_short, max_short)
long_break_seconds   = clamp(round(focus_seconds * 0.60), min_long,  max_long)
```

Where:
- `min_short`/`max_short` = minimum/maximum short break length (defaults: 60s / 1800s)
- `min_long`/`max_long`   = minimum/maximum long break length (defaults: 180s / 5400s)

## Flow-State Overtime Bonus

Any overtime earned (seconds spent beyond focus timer) is **added as a bonus to your next break**:

```
If next break is SHORT:
    bonus_seconds = round(overtime_seconds * 0.25)
If next break is LONG:
    bonus_seconds = round(overtime_seconds * 0.60)
```

## Multi-Worktree Swarm Architecture

| Worktree                | Role                  | Model/Worker          | Output File            |
|-------------------------|-----------------------|-----------------------|------------------------|
| worktree/worker-1-engine| Timer engine, storage | claude-sonnet-4.5     | pomodoro/engine.py, storage.py |
| worktree/worker-2-gui   | Tkinter GUI           | gpt-4.1               | pomodoro/gui.py, main.py|
| worktree/worker-3-cli   | CLI, pytest           | Qwen3.5-9B-Abliterated| pomodoro/cli.py, tests/test_core.py|

All implementations must match API contracts in [`spec.md`](./spec.md).

---

## Usage

```bash
# Desktop GUI
python main.py

# CLI calculations and stats
python -m pomodoro.cli --calc 50           # Calculate break values for 50m focus
python -m pomodoro.cli --status            # View current stats

# Self tests
python main.py --self-test                 # GUI/Engine/Storage test
python -m pomodoro.cli --self-test         # CLI self-test, engine+storage, exit 0 == OK
