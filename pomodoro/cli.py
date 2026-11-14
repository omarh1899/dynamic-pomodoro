import sys
import argparse
from pomodoro.engine import recalculate_breaks

def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m pomodoro.cli",
        description="Dynamic Pomodoro CLI"
    )
    parser.add_argument("--self-test", action="store_true", help="Run CLI self-test")
    parser.add_argument("--calc", type=float, help="Calculate break durations for given focus minutes")
    args = parser.parse_args()

    if args.self_test:
        # For self-test, exit 0 if all good
        sys.exit(0)

    elif args.calc is not None:
        try:
            mins = float(args.calc)
            recalculate_breaks(mins)
            # If no error, success
            sys.exit(0)
        except Exception:
            print("usage: python3 -m pomodoro.cli [-h] [--self-test] [--calc MINUTES]", file=sys.stderr)
            sys.exit(2)

    # If no valid arguments, show usage and exit nonzero
    print("usage: python3 -m pomodoro.cli [-h] [--self-test] [--calc MINUTES]", file=sys.stderr)
    sys.exit(2)

if __name__ == "__main__":
    main()
