# Worktree Worker Assignments

| Worktree                | Model/Worker              | Modules/Responsibility                    |
|-------------------------|--------------------------|-------------------------------------------|
| worktree/worker-1-engine| claude-sonnet-4.5        | `pomodoro/engine.py`, `pomodoro/storage.py` (timer state machine, break scaling, session stats) |
| worktree/worker-2-gui   | gpt-4.1                  | `pomodoro/gui.py`, `main.py` (Tkinter desktop GUI with all widgets, dark cyberpunk theme)       |
| worktree/worker-3-cli   | Qwen3.5-9B-Abliterated    | `pomodoro/cli.py`, `tests/test_core.py` (CLI entry, pytest/unittest, integration tests)          |

Each worker must implement the exact API contracts defined in [`spec.md`](./spec.md) and pass all relevant tests in `tests/test_core.py`. No interface, return value, or file location drift is permitted.

- **Engine/Storage** implements everything behind the APIs, with no GUI or CLI parsing.
- **GUI** imports `PomodoroEngine` and matches the live update requirements and theme.
- **CLI/Test** does all command-line and test integration, pinging the engine and storage.
