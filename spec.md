# Dynamic Pomodoro: Module and API Contracts

**All implementations must conform exactly for cross-worker compatibility.**

---

## `pomodoro/__init__.py`

- Exports: `PomodoroEngine`, `TimerState`, `recalculate_breaks` (from `pomodoro.engine`).

---

## `pomodoro/engine.py`

### `class TimerState(str, Enum)`
- States: `"IDLE"`, `"FOCUS"`, `"OVERTIME"`, `"SHORT_BREAK"`, `"LONG_BREAK"`, `"PAUSED"`

_Alternative_: Accept string constants if not using Enum.

### `def recalculate_breaks(focus_minutes: float, short_ratio: float = 0.20, long_ratio: float = 0.60, min_short_seconds: int = 60, max_short_seconds: int = 1800, min_long_seconds: int = 180, max_long_seconds: int = 5400) -> dict`
- Returns:
  ```
  {
    "focus_seconds": int,
    "short_break_seconds": int,
    "long_break_seconds": int
  }
  ```
- Logic:
  - `focus_seconds = round(focus_minutes * 60)`
  - Short break:  `short_break_seconds = clamp(round(focus_seconds * short_ratio), min_short_seconds, max_short_seconds)`
  - Long break:   `long_break_seconds  = clamp(round(focus_seconds * long_ratio), min_long_seconds, max_long_seconds)`
- Raises `ValueError` if `focus_minutes <= 0` or `focus_minutes > 240`.

### `class PomodoroEngine`
#### `__init__(self, focus_minutes: float = 25.0, cycles_before_long_break: int = 4, min_short_seconds: int = 60, max_short_seconds: int = 1800, min_long_seconds: int = 180, max_long_seconds: int = 5400)`
- **Attributes/Properties**:
  - `state` (starts `"IDLE"`)
  - `focus_seconds`
  - `short_break_seconds`
  - `long_break_seconds`
  - `remaining_seconds` (starts = `focus_seconds`)
  - `overtime_seconds` (starts = `0`)
  - `completed_cycles` (starts = `0`)
  - `cycles_before_long_break`

#### `set_focus_duration(self, focus_minutes: float) -> dict`
- Dynamically recalculates durations using `recalculate_breaks`
- If `state == "IDLE"`, also updates `remaining_seconds = self.focus_seconds`
- Returns break dict

#### `start(self) -> None`
- If in `"IDLE"` or `"PAUSED"`, sets state to `"FOCUS"` (or resumes previous active state if paused)

#### `pause(self) -> None`
- If active (`FOCUS`, `OVERTIME`, `SHORT_BREAK`, `LONG_BREAK`), saves state, sets `state = "PAUSED"`

#### `reset(self) -> None`
- `state = "IDLE"`
- `remaining_seconds = focus_seconds`
- `overtime_seconds = 0`

#### `add_overtime(self, minutes: float = 5.0) -> int`
- Adds `round(minutes * 60)` to `overtime_seconds`
- Raises `ValueError` if `minutes <= 0`
- If `state == "FOCUS"` and `remaining_seconds == 0`, or `state == "OVERTIME"`, keeps/sets `state = "OVERTIME"`
- Returns current `overtime_seconds`

#### `complete_focus(self) -> int`
- Increments `completed_cycles` by 1
- If `completed_cycles % cycles_before_long_break == 0`: next is `"LONG_BREAK"`, else `"SHORT_BREAK"`
- Calculates overtime bonus:
  - If next break is long: `round(overtime_seconds * 0.60)`
  - If next break is short: `round(overtime_seconds * 0.25)`
- Transitions to break, sets `remaining_seconds = (long/short_break_seconds) + bonus`
- Resets `overtime_seconds = 0`, returns new `remaining_seconds`

#### `tick(self, seconds: int = 1) -> str`
- Raises `ValueError` if `seconds < 0`
- In `"FOCUS"`:
  - Decrements `remaining_seconds`
  - If seconds > `remaining_seconds`, excess becomes `overtime_seconds`, `remaining_seconds = 0`, `state = "OVERTIME"`
  - If `remaining_seconds == 0`, `state = "OVERTIME"`
- In `"OVERTIME"`: adds `seconds` to overtime
- In `"SHORT_BREAK"`/`"LONG_BREAK"`: decrements `remaining_seconds` to 0; when 0, `state = "IDLE"`, `remaining_seconds = focus_seconds`
- Returns new `self.state`

---

## `pomodoro/storage.py`

### `class SessionStorage`
#### `__init__(self, path: str | Path = "session_stats.json")`
#### `load(self) -> dict`
#### `record_session(self, focus_minutes: float, overtime_minutes: float = 0.0) -> dict`
#### `reset_stats(self) -> dict`
- Stores/returns:
  ```
  {
    "completed_sessions": int,
    "total_focus_minutes": float,
    "total_overtime_minutes": float,
    "streak": int
  }
  ```

---

## `pomodoro/cli.py`

### `def main(argv: list[str] | None = None) -> int`
- Supported CLI args:
  - `--calc <focus_minutes>`: Prints break dict as JSON
  - `--status`: Prints stats as JSON
  - `--self-test`: Full engine + storage test; prints `SELF_TEST_OK`, returns `0`

---

## `pomodoro/gui.py`, `main.py`

- **Theme**: Tkinter GUI, dark neon (`#0f172a` bg, `#38bdf8` neon cyan, `#10b981` emerald).
- **Widgets**:
  - Focus duration slider & spinbox (`1` to `120`) - live recalc of breaks
  - Digital countdown (`MM:SS`)
  - Start / Pause / Reset buttons
  - "+5m Flow Overtime" button
  - "Skip / Take Break" button
  - Always-On-Top checkbox
  - Session stats footer
- `main.py --self-test`: Test engine & slider callback (run/destroy root after 150ms), prints `GUI_SELF_TEST_OK`, exits `0`.
