"""QLive CMAF/fMP4 segmenter.

Wraps FFmpeg to produce fragmented MP4 (fMP4) media fragments for live
streaming. Each fragment is a self-contained media segment that can be
wrapped in a QLive chunk for transport.

The segmenter reads from a video source (RTMP, device, or file) and
produces fragments at a configurable duration (500ms-2000ms per the
protocol spec).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Optional

from qlive.chunk import MAX_FRAGMENT_MS, MIN_FRAGMENT_MS

# Default segmenter parameters
DEFAULT_FRAGMENT_MS = 1000
DEFAULT_VIDEO_BITRATE = "4500k"
DEFAULT_AUDIO_BITRATE = "128k"
DEFAULT_FPS = 30
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080


class SegmenterError(Exception):
    """Base exception for segmenter errors."""


class SegmenterState(Enum):
    """Segmenter lifecycle states."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Segment:
    """A single media fragment produced by the segmenter."""

    data: bytes
    sequence_id: int
    timestamp: int
    duration_ms: int
    is_keyframe: bool = False

    @property
    def size(self) -> int:
        """Size of the segment data in bytes."""
        return len(self.data)


@dataclass
class SegmenterConfig:
    """Configuration for the FFmpeg segmenter."""

    source: str
    fragment_ms: int = DEFAULT_FRAGMENT_MS
    video_bitrate: str = DEFAULT_VIDEO_BITRATE
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    fps: int = DEFAULT_FPS
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    ffmpeg_path: str = "ffmpeg"
    extra_args: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (MIN_FRAGMENT_MS <= self.fragment_ms <= MAX_FRAGMENT_MS):
            raise SegmenterError(
                f"Fragment duration must be {MIN_FRAGMENT_MS}-{MAX_FRAGMENT_MS}ms"
            )


class Segmenter:
    """FFmpeg-based fMP4 segmenter for live streaming.

    Produces fragmented MP4 segments at a configurable duration. Each
    segment is a self-contained media fragment ready to be wrapped in
    a QLive chunk.

    Usage:
        segmenter = Segmenter(SegmenterConfig(source="rtmp://localhost/live"))
        async for segment in segmenter.segments():
            # Wrap segment in a QLive chunk and distribute
            pass
    """

    def __init__(self, config: SegmenterConfig) -> None:
        self.config = config
        self.state = SegmenterState.IDLE
        self._process: Optional[subprocess.Popen] = None
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._sequence = 0
        self._start_time: Optional[int] = None

    @property
    def sequence_id(self) -> int:
        """Current sequence ID (next segment to be produced)."""
        return self._sequence + 1

    @property
    def is_running(self) -> bool:
        """Whether the segmenter is actively producing segments."""
        return self.state == SegmenterState.RUNNING

    async def start(self) -> None:
        """Start the FFmpeg process."""
        if self.state in (SegmenterState.RUNNING, SegmenterState.STARTING):
            return

        self.state = SegmenterState.STARTING
        self._temp_dir = tempfile.TemporaryDirectory(prefix="qlive-seg-")
        self._sequence = 0
        self._start_time = int(time.time() * 1000)

        # Build FFmpeg command
        cmd = self._build_command()

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.state = SegmenterState.RUNNING
        except FileNotFoundError as e:
            self.state = SegmenterState.ERROR
            raise SegmenterError(
                f"FFmpeg not found at '{self.config.ffmpeg_path}'. "
                "Install FFmpeg or set ffmpeg_path in config."
            ) from e

    async def stop(self) -> None:
        """Stop the FFmpeg process gracefully."""
        if self.state in (SegmenterState.IDLE, SegmenterState.STOPPED):
            return

        self.state = SegmenterState.STOPPING
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None

        if self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None

        self.state = SegmenterState.STOPPED

    async def segments(self) -> AsyncIterator[Segment]:
        """Yield media segments as they are produced.

        Each segment is a complete fMP4 fragment ready for chunking.
        """
        if not self.is_running:
            await self.start()

        assert self._temp_dir is not None
        pattern = os.path.join(self._temp_dir.name, "seg_%05d.m4s")
        seen: set[str] = set()

        try:
            while self.is_running:
                # Find new segment files
                for path in sorted(Path(self._temp_dir.name).glob("seg_*.m4s")):
                    if str(path) in seen:
                        continue
                    seen.add(str(path))

                    data = path.read_bytes()
                    if not data:
                        continue

                    self._sequence += 1
                    yield Segment(
                        data=data,
                        sequence_id=self._sequence,
                        timestamp=self._start_time
                        + (self._sequence - 1) * self.config.fragment_ms,
                        duration_ms=self.config.fragment_ms,
                    )

                await asyncio.sleep(0.05)
        finally:
            await self.stop()

    def _build_command(self) -> list[str]:
        """Build the FFmpeg command line."""
        cfg = self.config
        return [
            cfg.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            cfg.source,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "zerolatency",
            "-b:v",
            cfg.video_bitrate,
            "-c:a",
            "aac",
            "-b:a",
            cfg.audio_bitrate,
            "-f",
            "fmp4",
            "-movflags",
            "frag_keyframe+empty_moov+default_base_moof",
            "-frag_duration",
            str(cfg.fragment_ms * 1000),  # microseconds
            "-r",
            str(cfg.fps),
            "-s",
            f"{cfg.width}x{cfg.height}",
            *cfg.extra_args,
            os.path.join(self._temp_dir.name, "seg_%05d.m4s"),
        ]

    def __repr__(self) -> str:
        return (
            f"Segmenter(source={self.config.source!r}, "
            f"fragment_ms={self.config.fragment_ms}, "
            f"state={self.state.value})"
        )