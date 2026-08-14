"""QLive command-line interface."""

import argparse
import asyncio
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.broadcaster import Broadcaster, BroadcasterConfig
from qlive.viewer import Viewer


def load_private_key(key_path: str) -> ed25519.Ed25519PrivateKey:
    """Load an Ed25519 private key from a PEM file."""
    try:
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    except FileNotFoundError:
        print(f"Error: Key file not found: {key_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to load key: {e}", file=sys.stderr)
        sys.exit(1)


async def run_broadcast(args: argparse.Namespace) -> int:
    """Run the broadcaster."""
    private_key = load_private_key(args.key)

    config = BroadcasterConfig(
        qortal_name=args.name,
        source=args.source,
        title=args.title or args.name,
        description=args.description or "",
        category=args.category or "other",
        fragment_ms=args.fragment_ms,
        video_bitrate=args.video_bitrate,
        audio_bitrate=args.audio_bitrate,
        fps=args.fps,
        width=args.width,
        height=args.height,
        ffmpeg_path=args.ffmpeg,
        archive_to_vod=not args.no_archive,
    )

    broadcaster = Broadcaster(config, private_key)
    print(f"Starting broadcast as '{args.name}' from {args.source}...")

    try:
        await broadcaster.run()
    except KeyboardInterrupt:
        print("\nStopping broadcast...")
        await broadcaster.stop()

    print(f"Broadcast ended. {broadcaster.stats.segments_produced} segments produced.")
    return 0


async def run_watch(args: argparse.Namespace) -> int:
    """Run the viewer."""
    # Parse stream identifier: qortal://name/stream or hex stream ID
    stream_id = None
    if args.stream.startswith("qortal://"):
        # In a real implementation, this would resolve the stream ID from QDN
        print(f"Resolving stream: {args.stream}")
        # For now, derive a placeholder stream ID
        import hashlib

        stream_id = hashlib.sha256(args.stream.encode()).digest()
    else:
        try:
            stream_id = bytes.fromhex(args.stream)
        except ValueError:
            print(f"Error: Invalid stream ID: {args.stream}", file=sys.stderr)
            return 1

    viewer = Viewer(node_id=args.node or "qlive-viewer")
    print(f"Connecting to stream {stream_id.hex()[:16]}...")

    try:
        viewer.connect(stream_id)
        print("Connected. Press Ctrl+C to disconnect.")

        # In a real implementation, this would receive chunks from the swarm
        # For now, just wait for interruption
        while True:
            await asyncio.sleep(1)
            viewer.check_buffer_health()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        viewer.disconnect()

    print(f"Disconnected. {viewer.stats.chunks_received} chunks received.")
    return 0


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
    broadcast_parser.add_argument("--key", required=True, help="Path to Ed25519 private key (PEM)")
    broadcast_parser.add_argument("--title", help="Stream title (defaults to name)")
    broadcast_parser.add_argument("--description", help="Stream description")
    broadcast_parser.add_argument("--category", help="Stream category")
    broadcast_parser.add_argument("--fragment-ms", type=int, default=1000, help="Fragment duration in ms")
    broadcast_parser.add_argument("--video-bitrate", default="4500k", help="Video bitrate")
    broadcast_parser.add_argument("--audio-bitrate", default="128k", help="Audio bitrate")
    broadcast_parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    broadcast_parser.add_argument("--width", type=int, default=1920, help="Video width")
    broadcast_parser.add_argument("--height", type=int, default=1080, help="Video height")
    broadcast_parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg binary path")
    broadcast_parser.add_argument("--no-archive", action="store_true", help="Disable VOD archival")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch a live stream")
    watch_parser.add_argument(
        "--stream", required=True, help="Stream identifier (qortal://name/stream or hex ID)"
    )
    watch_parser.add_argument("--node", help="Node ID for this viewer")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "broadcast":
        return asyncio.run(run_broadcast(args))
    elif args.command == "watch":
        return asyncio.run(run_watch(args))

    return 0


if __name__ == "__main__":
    sys.exit(main())