import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dynamic Pomodoro CLI")
    parser.add_argument("--self-test", action="store_true", help="Run CLI self-test")
    args = parser.parse_args()
    if args.self_test:
        # Minimal self-test: import core modules and exit 0 if all is well
        try:
            from pomodoro.engine import PomodoroEngine, recalculate_breaks, TimerState
            from pomodoro.storage import SessionStorage
        except Exception as e:
            print("Self-test failed:", e, file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    parser.print_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
