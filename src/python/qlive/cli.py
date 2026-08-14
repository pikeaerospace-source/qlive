"""QLive command-line interface."""

import argparse
import sys


def main() -> int:
    """QLive CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="qlive",
        description="Decentralized live streaming for the Qortal network",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('qlive').__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Broadcast command
    broadcast_parser = subparsers.add_parser(
        "broadcast", help="Start a live broadcast"
    )
    broadcast_parser.add_argument(
        "--name", required=True, help="Qortal Name to broadcast under"
    )
    broadcast_parser.add_argument(
        "--source", required=True, help="Video source (RTMP URL, device, or file)"
    )

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch a live stream")
    watch_parser.add_argument(
        "--stream", required=True, help="Stream identifier (qortal://name/stream)"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "broadcast":
        print(f"Broadcast not yet implemented: {args.name} from {args.source}")
    elif args.command == "watch":
        print(f"Watch not yet implemented: {args.stream}")

    return 0


if __name__ == "__main__":
    sys.exit(main())