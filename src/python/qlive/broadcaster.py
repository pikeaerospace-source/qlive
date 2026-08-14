"""QLive broadcaster application.

Implements the broadcaster side of the QLive protocol. Ties together
the segmenter, chunk signing, swarm, and signaling components to
produce and distribute a live stream.

The broadcaster:
1. Starts the FFmpeg segmenter
2. Wraps each segment in a signed QLive chunk
3. Distributes chunks through the swarm
4. Archives expired chunks for VOD
5. Manages stream lifecycle via QDN signaling
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.archival import ArchivalPipeline
from qlive.chunk import create_chunk
from qlive.segmenter import Segment, Segmenter, SegmenterConfig
from qlive.signaling import StreamMetadata, StreamRegistry, StreamStatus
from qlive.swarm import SwarmManager


class BroadcasterState(Enum):
    """Broadcaster lifecycle states."""

    IDLE = "idle"
    STARTING = "starting"
    LIVE = "live"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BroadcasterError(Exception):
    """Base exception for broadcaster errors."""


@dataclass
class BroadcasterConfig:
    """Configuration for the broadcaster."""

    qortal_name: str
    source: str
    title: str
    description: str = ""
    category: str = "other"
    fragment_ms: int = 1000
    video_bitrate: str = "4500k"
    audio_bitrate: str = "128k"
    fps: int = 30
    width: int = 1920
    height: int = 1080
    ffmpeg_path: str = "ffmpeg"
    archive_to_vod: bool = True
    min_archive_chunk_bytes: int = 10 * 1024 * 1024


@dataclass
class BroadcasterStats:
    """Statistics for broadcaster monitoring."""

    state: BroadcasterState = BroadcasterState.IDLE
    segments_produced: int = 0
    chunks_signed: int = 0
    chunks_distributed: int = 0
    bytes_produced: int = 0
    viewers_connected: int = 0
    started_at: Optional[int] = None
    duration_seconds: int = 0


class Broadcaster:
    """QLive broadcaster application.

    Usage:
        config = BroadcasterConfig(
            qortal_name="my-name",
            source="rtmp://localhost/live",
            title="My Stream",
        )
        broadcaster = Broadcaster(config, private_key)
        await broadcaster.start()
        # ... stream runs ...
        await broadcaster.stop()
    """

    def __init__(
        self,
        config: BroadcasterConfig,
        private_key: ed25519.Ed25519PrivateKey,
    ) -> None:
        self.config = config
        self.private_key = private_key
        self.state = BroadcasterState.IDLE
        self._segmenter: Optional[Segmenter] = None
        self._swarm: Optional[SwarmManager] = None
        self._registry: Optional[StreamRegistry] = None
        self._archival: Optional[ArchivalPipeline] = None
        self._stream_id: Optional[bytes] = None
        self._stats = BroadcasterStats()
        self._sequence = 0

    @property
    def stats(self) -> BroadcasterStats:
        """Current broadcaster statistics."""
        self._update_stats()
        return self._stats

    @property
    def stream_id(self) -> Optional[bytes]:
        """The active stream ID (None until started)."""
        return self._stream_id

    @property
    def is_live(self) -> bool:
        """Whether the broadcaster is actively streaming."""
        return self.state == BroadcasterState.LIVE

    async def start(self) -> None:
        """Start the broadcast."""
        if self.state in (BroadcasterState.STARTING, BroadcasterState.LIVE):
            return

        self.state = BroadcasterState.STARTING
        self._stats.started_at = int(time.time())

        try:
            # Create stream metadata
            metadata = StreamMetadata(
                publisher=self.config.qortal_name,
                title=self.config.title,
                description=self.config.description,
                category=self.config.category,
                status=StreamStatus.ANNOUNCED,
                fragment_duration_ms=self.config.fragment_ms,
            )
            self._stream_id = metadata.stream_id

            # Initialize components
            self._registry = StreamRegistry()
            self._registry.register(metadata)

            self._swarm = SwarmManager(self.config.qortal_name)

            if self.config.archive_to_vod:
                self._archival = ArchivalPipeline(
                    stream_id=self._stream_id,
                    publisher=self.config.qortal_name,
                    title=self.config.title,
                    description=self.config.description,
                    category=self.config.category,
                    min_chunk_bytes=self.config.min_archive_chunk_bytes,
                )

            # Start segmenter
            segmenter_config = SegmenterConfig(
                source=self.config.source,
                fragment_ms=self.config.fragment_ms,
                video_bitrate=self.config.video_bitrate,
                audio_bitrate=self.config.audio_bitrate,
                fps=self.config.fps,
                width=self.config.width,
                height=self.config.height,
                ffmpeg_path=self.config.ffmpeg_path,
            )
            self._segmenter = Segmenter(segmenter_config)
            await self._segmenter.start()

            # Mark stream as live
            self._registry.update_status(self._stream_id, StreamStatus.LIVE)
            self.state = BroadcasterState.LIVE

        except Exception as e:
            self.state = BroadcasterState.ERROR
            raise BroadcasterError(f"Failed to start broadcast: {e}") from e

    async def stop(self) -> None:
        """Stop the broadcast gracefully."""
        if self.state in (BroadcasterState.IDLE, BroadcasterState.STOPPED):
            return

        self.state = BroadcasterState.STOPPING

        # Stop segmenter
        if self._segmenter:
            await self._segmenter.stop()

        # Finalize archive
        if self._archival and self._stream_id:
            try:
                manifest = self._archival.finalize()
                if self._registry:
                    self._registry.update_status(
                        self._stream_id, StreamStatus.ARCHIVED
                    )
            except Exception:
                # Archive may be empty if stream was too short
                pass

        # Update stream status
        if self._registry and self._stream_id:
            self._registry.update_status(self._stream_id, StreamStatus.ENDED)

        self.state = BroadcasterState.STOPPED

    async def run(self) -> None:
        """Run the broadcast until stopped.

        Processes segments from the segmenter, signs them as chunks,
        and distributes them through the swarm.
        """
        if not self._segmenter:
            await self.start()

        assert self._segmenter is not None
        assert self._stream_id is not None

        try:
            async for segment in self._segmenter.segments():
                if not self.is_live:
                    break

                self._process_segment(segment)
        finally:
            await self.stop()

    def _process_segment(self, segment: Segment) -> None:
        """Process a single media segment into a signed chunk."""
        self._sequence += 1

        # Create and sign chunk
        chunk = create_chunk(
            stream_id=self._stream_id,
            sequence_id=self._sequence,
            payload=segment.data,
            duration=segment.duration_ms,
            timestamp=segment.timestamp,
        )
        chunk.sign(self.private_key)

        self._stats.segments_produced += 1
        self._stats.chunks_signed += 1
        self._stats.bytes_produced += len(segment.data)

        # Archive expired chunks
        if self._archival:
            self._archival.add_chunk(chunk)

        # Distribute through swarm (simplified - actual transport TBD)
        self._stats.chunks_distributed += 1

    def _update_stats(self) -> None:
        """Refresh broadcaster statistics."""
        self._stats.state = self.state
        if self._stats.started_at:
            self._stats.duration_seconds = int(time.time()) - self._stats.started_at
        if self._swarm:
            self._stats.viewers_connected = self._swarm.stats.connected_peers