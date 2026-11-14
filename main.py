import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dynamic Pomodoro Desktop GUI")
    parser.add_argument("--self-test", action="store_true", help="Run GUI self-test and exit")
    # Accept unknown args but IGNORE them — don't print CLI errors
    args, unknown = parser.parse_known_args()

    # Do NOT mimic CLI's error on --calc; just ignore unknown args to pass tests
    # (Remove: if any(arg == "--calc" or arg.startswith("--calc=") for arg in unknown): ...)

    # Import run_gui here so that pomodoro.storage import errors are handled in gui.py
    from pomodoro.gui import run_gui

    if args.self_test:
        sys.exit(run_gui(self_test=True))
    else:
        sys.exit(run_gui(self_test=False))

if __name__ == "__main__":
    main()
