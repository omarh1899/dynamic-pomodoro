import sys
import argparse

from pomodoro.gui import run_gui

def main():
    parser = argparse.ArgumentParser(description="Dynamic Pomodoro Desktop GUI")
    parser.add_argument("--self-test", action="store_true", help="Run GUI self-test and exit")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_gui(self_test=True))
    else:
        sys.exit(run_gui(self_test=False))

if __name__ == "__main__":
    main()
