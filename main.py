import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dynamic Pomodoro Desktop GUI")
    parser.add_argument("--self-test", action="store_true", help="Run GUI self-test and exit")
    args, unknown = parser.parse_known_args()

    from pomodoro.gui import run_gui

    if args.self_test:
        sys.exit(run_gui(self_test=True))
    else:
        sys.exit(run_gui(self_test=False))

if __name__ == "__main__":
    main()
