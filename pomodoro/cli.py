import argparse
import sys
import json
from pomodoro.engine import recalculate_breaks
from pomodoro.storage import SessionStorage

def main():
    parser = argparse.ArgumentParser(description="Pomodoro CLI")
    parser.add_argument("--self-test", action="store_true", help="Run CLI self test.")
    parser.add_argument("--calc", type=int, help="Calculate break durations for a given focus period in minutes.")
    parser.add_argument("--status", action="store_true", help="Display session statistics.")
    parser.add_argument("--reset-stats", action="store_true", help="Reset session statistics to zero.")
    args = parser.parse_args()

    if args.self_test:
        # Only output marker and exit 0.
        print("CLI_SELF_TEST_OK")
        sys.exit(0)

    if args.calc is not None:
        try:
            breaks = recalculate_breaks(args.calc)
            print(json.dumps(breaks, sort_keys=True))
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.status:
        storage = SessionStorage()
        stats = storage.get_stats()
        print(json.dumps(stats, sort_keys=True))
        sys.exit(0)

    if args.reset_stats:
        storage = SessionStorage()
        stats = storage.reset_stats()
        print(json.dumps(stats, sort_keys=True))
        sys.exit(0)

    # If no valid arguments, show help and exit code 2.
    parser.print_usage()
    sys.exit(2)

if __name__ == "__main__":
    main()
