import unittest
import sys
import subprocess
from pomodoro.engine import recalculate_breaks, PomodoroEngine, TimerState

class TestPomodoroAdversarial(unittest.TestCase):
    # 1. Minimum/maximum clamping in recalculate_breaks
    def test_recalculate_breaks_minimum_clamping(self):
        # 1-minute focus: short break should clamp to min_short_seconds=60, long break to min_long_seconds=180
        breaks = recalculate_breaks(1)
        self.assertEqual(breaks["focus_seconds"], 60)
        self.assertEqual(breaks["short_break_seconds"], 60)
        self.assertEqual(breaks["long_break_seconds"], 180)

    def test_recalculate_breaks_maximum_clamping(self):
        # 180-minute focus: short break should clamp to max_short_seconds=1800, long break to max_long_seconds=5400
        breaks = recalculate_breaks(180)
        self.assertEqual(breaks["focus_seconds"], 10800)
        self.assertEqual(breaks["short_break_seconds"], 1800)
        self.assertEqual(breaks["long_break_seconds"], 5400)

    def test_recalculate_breaks_no_clamping_in_middle(self):
        # 50-minute focus: should not clamp, should be proportional
        breaks = recalculate_breaks(50)
        self.assertEqual(breaks["focus_seconds"], 3000)
        self.assertEqual(breaks["short_break_seconds"], 600)
        self.assertEqual(breaks["long_break_seconds"], 1800)

    # 2. Invalid inputs raising ValueError
    def test_recalculate_breaks_zero(self):
        with self.assertRaises(ValueError):
            recalculate_breaks(0)

    def test_recalculate_breaks_negative(self):
        with self.assertRaises(ValueError):
            recalculate_breaks(-10)

    def test_recalculate_breaks_too_large(self):
        with self.assertRaises(ValueError):
            recalculate_breaks(300)

    def test_engine_tick_negative(self):
        eng = PomodoroEngine()
        eng.start()
        with self.assertRaises(ValueError):
            eng.tick(-5)

    def test_engine_add_overtime_zero(self):
        eng = PomodoroEngine()
        with self.assertRaises(ValueError):
            eng.add_overtime(0)

    def test_engine_add_overtime_negative(self):
        eng = PomodoroEngine()
        with self.assertRaises(ValueError):
            eng.add_overtime(-3)

    # 3. Excess tick rollover into overtime
    def test_tick_rollover_into_overtime(self):
        eng = PomodoroEngine(focus_minutes=1)
        eng.start()
        eng.remaining_seconds = 10
        state = eng.tick(25)
        self.assertEqual(eng.remaining_seconds, 0)
        self.assertEqual(eng.state, "OVERTIME")
        self.assertEqual(eng.overtime_seconds, 15)
        self.assertEqual(state, "OVERTIME")

    # 4. Pause/resume preservation
    def test_pause_resume_preservation(self):
        eng = PomodoroEngine(focus_minutes=1)
        eng.start()
        eng.remaining_seconds = 30
        eng.pause()
        self.assertEqual(eng.state, "PAUSED")
        before = eng.remaining_seconds
        eng.tick(10)
        # Should not decrement while paused
        self.assertEqual(eng.remaining_seconds, before)
        # Resume
        eng.start()
        self.assertEqual(eng.state, "FOCUS")
        eng.tick(5)
        self.assertEqual(eng.remaining_seconds, before - 5)

    # 5. 4-cycle long break cadence
    def test_long_break_cadence(self):
        eng = PomodoroEngine(focus_minutes=1, cycles_before_long_break=4)
        eng.state = "FOCUS"
        eng.remaining_seconds = 0
        eng.overtime_seconds = 0
        # Simulate 3 cycles: should get SHORT_BREAK
        for i in range(1, 4):
            eng.completed_cycles = i - 1
            eng.state = "FOCUS"
            eng.remaining_seconds = 0
            rem = eng.complete_focus()
            self.assertEqual(eng.state, "SHORT_BREAK", f"Cycle {i} should be SHORT_BREAK")
            # Fast forward through break
            eng.remaining_seconds = 0
            eng.state = "IDLE"
        # 4th cycle: should get LONG_BREAK
        eng.completed_cycles = 3
        eng.state = "FOCUS"
        eng.remaining_seconds = 0
        rem = eng.complete_focus()
        self.assertEqual(eng.state, "LONG_BREAK", "4th cycle should be LONG_BREAK")

    # 6. CLI --calc 50 returns exit code 0
    def test_cli_calc_50_exit_code(self):
        # This assumes the CLI is available as a module and supports --calc
        code = subprocess.call([sys.executable, "-m", "pomodoro.cli", "--calc", "50"])
        self.assertEqual(code, 0)

if __name__ == "__main__":
    unittest.main()
