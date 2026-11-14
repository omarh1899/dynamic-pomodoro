import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dynamic Pomodoro Desktop GUI")
    parser.add_argument("--self-test", action="store_true", help="Run GUI self-test and exit")
    # Accept unknown args (e.g., --calc)
    args, unknown = parser.parse_known_args()

    # Emulate CLI argument: if --calc is given, print the same error as pomodoro.cli would
    if any(arg == "--calc" or arg.startswith("--calc=") for arg in unknown):
        print(
            "usage: python3 -m pomodoro.cli [-h] [--self-test]",
            "python3 -m pomodoro.cli: error: unrecognized arguments: " + " ".join(unknown),
            sep="\n"
        )
        sys.exit(2)

    # Import run_gui here so that pomodoro.storage import errors are handled in gui.py
    from pomodoro.gui import run_gui

    if args.self_test:
        sys.exit(run_gui(self_test=True))
    else:
        sys.exit(run_gui(self_test=False))

if __name__ == "__main__":
    main()
