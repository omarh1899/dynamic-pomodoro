import unittest
import json
from pomodoro.engine import PomodoroEngine, recalculate_breaks, TimerState
from pomodoro.storage import SessionStorage
import tempfile
import shutil
import sys
import os

class TestPomodoroCore(unittest.TestCase):
    def test_baseline_25m(self):
        breaks = recalculate_breaks(25)
        self.assertEqual(breaks, {
            "focus_seconds": 1500,
            "short_break_seconds": 300,
            "long_break_seconds": 900
        })

    def test_dynamic_50m(self):
        breaks = recalculate_breaks(50)
        self.assertEqual(breaks, {
            "focus_seconds": 3000,
            "short_break_seconds": 600,
            "long_break_seconds": 1800
        })

    def test_dynamic_10m(self):
        breaks = recalculate_breaks(10)
        self.assertEqual(breaks, {
            "focus_seconds": 600,
            "short_break_seconds": 120,
            "long_break_seconds": 360
        })

    def test_overtime_bonus(self):
        eng = PomodoroEngine(focus_minutes=25)
        eng.state = "FOCUS"
        eng.remaining_seconds = 0               # Simulate finished focus
        eng.overtime_seconds = 480              # 8 min overtime
        eng.completed_cycles = 3
        # Next is long break (4th cycle)
        rem = eng.complete_focus()
        self.assertEqual(rem, 900 + round(480 * 0.60))      # 900 + 288 = 1188

        eng = PomodoroEngine(focus_minutes=25)
        eng.state = "FOCUS"
        eng.remaining_seconds = 0
        eng.overtime_seconds = 480
        eng.completed_cycles = 2
        # Next is short break
        rem = eng.complete_focus()
        self.assertEqual(rem, 300 + round(480 * 0.25))      # 300 + 120 = 420

    def test_tick_transitions(self):
        eng = PomodoroEngine(focus_minutes=25)
        # IDLE -> FOCUS
        eng.start()
        self.assertEqual(eng.state, "FOCUS")
        # FOCUS -> OVERTIME
        eng.remaining_seconds = 1
        state = eng.tick(1)
        self.assertEqual(state, "OVERTIME")
        # OVERTIME accumulates time
        eng.tick(10)
        self.assertEqual(eng.overtime_seconds, 10)
        # End period
        eng.completed_cycles = 0
        eng.overtime_seconds = 240
        eng.state = "FOCUS"
        eng.remaining_seconds = 0
        eng.complete_focus()
        self.assertIn(eng.state, ("SHORT_BREAK", "LONG_BREAK"))
        # Break -> IDLE after countdown
        eng.remaining_seconds = 1
        state = eng.tick(1)
        self.assertEqual(state, "IDLE")
        self.assertEqual(eng.remaining_seconds, eng.focus_seconds)

    def test_storage_persistence(self):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test_stats.json")
        storage = SessionStorage(path=path)
        data = storage.record_session(25, 5)
        self.assertEqual(data["completed_sessions"], 1)
        self.assertAlmostEqual(data["total_focus_minutes"], 25)
        self.assertAlmostEqual(data["total_overtime_minutes"], 5)
        self.assertEqual(data["streak"], 1)
        # Reset stats
        data = storage.reset_stats()
        self.assertEqual(data, {"completed_sessions": 0, "total_focus_minutes": 0.0, "total_overtime_minutes": 0.0, "streak": 0})
        shutil.rmtree(tmpdir)

    def test_cli_self_test(self):
        # Ensures CLI entrypoint self-test executes and returns 0
        import subprocess
        code = subprocess.call([sys.executable, "-m", "pomodoro.cli", "--self-test"])
        self.assertEqual(code, 0)

if __name__ == "__main__":
    unittest.main()
