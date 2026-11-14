import math
from enum import Enum

def clamp(val, min_, max_):
    return min(max(val, min_), max_)

class TimerState(str, Enum):
    IDLE = "IDLE"
    FOCUS = "FOCUS"
    OVERTIME = "OVERTIME"
    SHORT_BREAK = "SHORT_BREAK"
    LONG_BREAK = "LONG_BREAK"
    PAUSED = "PAUSED"

def recalculate_breaks(
    focus_minutes: float,
    short_ratio: float = 0.20,
    long_ratio: float = 0.60,
    min_short_seconds: int = 60,
    max_short_seconds: int = 1800,
    min_long_seconds: int = 180,
    max_long_seconds: int = 5400
) -> dict:
    if focus_minutes <= 0 or focus_minutes > 240:
        raise ValueError("focus_minutes must be in (0, 240]")
    focus_seconds = round(focus_minutes * 60)
    short_break_seconds = clamp(
        round(focus_seconds * short_ratio), min_short_seconds, max_short_seconds
    )
    long_break_seconds = clamp(
        round(focus_seconds * long_ratio), min_long_seconds, max_long_seconds
    )
    return {
        "focus_seconds": focus_seconds,
        "short_break_seconds": short_break_seconds,
        "long_break_seconds": long_break_seconds
    }

class PomodoroEngine:
    def __init__(
        self,
        focus_minutes: float = 25.0,
        cycles_before_long_break: int = 4,
        min_short_seconds: int = 60,
        max_short_seconds: int = 1800,
        min_long_seconds: int = 180,
        max_long_seconds: int = 5400
    ):
        self._min_short_seconds = min_short_seconds
        self._max_short_seconds = max_short_seconds
        self._min_long_seconds = min_long_seconds
        self._max_long_seconds = max_long_seconds
        self.cycles_before_long_break = cycles_before_long_break
        self.breaks = recalculate_breaks(
            focus_minutes=focus_minutes,
            min_short_seconds=min_short_seconds,
            max_short_seconds=max_short_seconds,
            min_long_seconds=min_long_seconds,
            max_long_seconds=max_long_seconds
        )
        self.focus_seconds = self.breaks["focus_seconds"]
        self.short_break_seconds = self.breaks["short_break_seconds"]
        self.long_break_seconds = self.breaks["long_break_seconds"]
        self.state = TimerState.IDLE
        self.remaining_seconds = self.focus_seconds
        self.overtime_seconds = 0
        self.completed_cycles = 0
        self._last_active_state = None

    def set_focus_duration(self, focus_minutes: float) -> dict:
        breaks = recalculate_breaks(
            focus_minutes=focus_minutes,
            min_short_seconds=self._min_short_seconds,
            max_short_seconds=self._max_short_seconds,
            min_long_seconds=self._min_long_seconds,
            max_long_seconds=self._max_long_seconds
        )
        self.focus_seconds = breaks["focus_seconds"]
        self.short_break_seconds = breaks["short_break_seconds"]
        self.long_break_seconds = breaks["long_break_seconds"]
        self.breaks = breaks
        if self.state == TimerState.IDLE:
            self.remaining_seconds = self.focus_seconds
        return breaks

    def start(self) -> None:
        if self.state == TimerState.IDLE or self.state == TimerState.PAUSED:
            # Resume the last active state if paused
            if self.state == TimerState.PAUSED and self._last_active_state:
                self.state = self._last_active_state
                self._last_active_state = None
            else:
                self.state = TimerState.FOCUS

    def pause(self) -> None:
        # Only pause if currently in an active period (not IDLE or PAUSED)
        if self.state in (
            TimerState.FOCUS, TimerState.OVERTIME, TimerState.SHORT_BREAK, TimerState.LONG_BREAK
        ):
            self._last_active_state = self.state
            self.state = TimerState.PAUSED

    def reset(self) -> None:
        self.state = TimerState.IDLE
        self.remaining_seconds = self.focus_seconds
        self.overtime_seconds = 0

    def add_overtime(self, minutes: float = 5.0) -> int:
        if minutes <= 0:
            raise ValueError("minutes for overtime must be > 0")
        additional = round(minutes * 60)
        self.overtime_seconds += additional
        # If in FOCUS and already finished, or in OVERTIME, set state to OVERTIME
        if (
            (self.state == TimerState.FOCUS and self.remaining_seconds == 0)
        ) or (self.state == TimerState.OVERTIME):
            self.state = TimerState.OVERTIME
        return self.overtime_seconds

    def complete_focus(self) -> int:
        self.completed_cycles += 1
        # Determine next break type
        if self.completed_cycles % self.cycles_before_long_break == 0:
            next_break_state = TimerState.LONG_BREAK
            break_base = self.long_break_seconds
            bonus = round(self.overtime_seconds * 0.60)
        else:
            next_break_state = TimerState.SHORT_BREAK
            break_base = self.short_break_seconds
            bonus = round(self.overtime_seconds * 0.25)
        self.state = next_break_state
        self.remaining_seconds = break_base + bonus
        self.overtime_seconds = 0
        return self.remaining_seconds

    def tick(self, seconds: int = 1) -> str:
        if seconds < 0:
            raise ValueError("seconds for tick must be >= 0")
        if self.state == TimerState.PAUSED:
            # Do nothing while paused
            return self.state.value
        if self.state == TimerState.FOCUS:
            # Subtract from remaining_seconds. If goes negative, remainder is overtime
            if self.remaining_seconds > seconds:
                self.remaining_seconds -= seconds
            else:
                excess = seconds - self.remaining_seconds
                if self.remaining_seconds > 0:
                    self.remaining_seconds = 0
                else:
                    excess = seconds
                self.state = TimerState.OVERTIME
                self.overtime_seconds += excess
        elif self.state == TimerState.OVERTIME:
            self.overtime_seconds += seconds
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            if self.remaining_seconds > seconds:
                self.remaining_seconds -= seconds
            else:
                self.remaining_seconds = self.focus_seconds
                self.state = TimerState.IDLE
        # If just hit zero in focus, switch to overtime
        if self.state == TimerState.FOCUS and self.remaining_seconds == 0:
            self.state = TimerState.OVERTIME
        return self.state.value
