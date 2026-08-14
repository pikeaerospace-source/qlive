"""QLive RAM sliding-window buffer.

Implements the in-memory rolling buffer defined in docs/protocol.md section 6.

Fragments are stored strictly in RAM and evicted oldest-first once they
fall outside the active window. The buffer never touches disk.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum

from qlive.chunk import Chunk

# Buffer parameters (from docs/protocol.md section 6.2)
DEFAULT_BUFFER_SECONDS = 45
MIN_BUFFER_SECONDS = 30
MAX_BUFFER_SECONDS = 60
DEFAULT_MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB


class BufferState(Enum):
    """Buffer health states."""

    FILLING = "filling"
    HEALTHY = "healthy"
    STALLING = "stalling"
    OVERFLOW = "overflow"


class BufferError(Exception):
    """Base exception for buffer errors."""


class BufferFullError(BufferError):
    """Raised when the buffer exceeds its memory limit."""


class BufferGapError(BufferError):
    """Raised when a sequence gap is detected."""


@dataclass
class BufferStats:
    """Statistics for buffer monitoring."""

    total_chunks: int = 0
    total_bytes: int = 0
    window_seconds: int = DEFAULT_BUFFER_SECONDS
    state: BufferState = BufferState.FILLING
    oldest_sequence: int | None = None
    newest_sequence: int | None = None
    oldest_timestamp: int | None = None
    newest_timestamp: int | None = None
    gaps: list[tuple[int, int]] = field(default_factory=list)

    @property
    def fill_ratio(self) -> float:
        """Ratio of current window coverage to target window size."""
        if self.oldest_timestamp is None or self.newest_timestamp is None:
            return 0.0
        span = (self.newest_timestamp - self.oldest_timestamp) / 1000.0
        return min(span / self.window_seconds, 1.0)


class SlidingWindowBuffer:
    """In-memory rolling buffer for live stream fragments.

    Stores chunks in an ordered map keyed by sequence ID. Chunks older
    than the window are evicted oldest-first. The buffer is strictly
    RAM-only — nothing is ever written to disk.
    """

    def __init__(
        self,
        window_seconds: int = DEFAULT_BUFFER_SECONDS,
        max_memory_bytes: int = DEFAULT_MAX_MEMORY_BYTES,
    ) -> None:
        if not (MIN_BUFFER_SECONDS <= window_seconds <= MAX_BUFFER_SECONDS):
            raise BufferError(f"Window must be {MIN_BUFFER_SECONDS}-{MAX_BUFFER_SECONDS}s")
        self.window_seconds = window_seconds
        self.max_memory_bytes = max_memory_bytes
        self._chunks: OrderedDict[int, Chunk] = OrderedDict()
        self._total_bytes = 0
        self._last_eviction = 0.0
        self._stats = BufferStats(window_seconds=window_seconds)

    @property
    def stats(self) -> BufferStats:
        """Current buffer statistics."""
        self._update_stats()
        return self._stats

    @property
    def state(self) -> BufferState:
        """Current buffer state."""
        return self.stats.state

    @property
    def size(self) -> int:
        """Number of chunks in the buffer."""
        return len(self._chunks)

    @property
    def memory_usage(self) -> int:
        """Total bytes of chunk payloads in the buffer."""
        return self._total_bytes

    def add(self, chunk: Chunk) -> None:
        """Add a chunk to the buffer.

        Raises:
            BufferGapError: If the chunk creates a sequence gap.
            BufferFullError: If the buffer exceeds its memory limit.
        """
        # Check for sequence gaps
        if self._chunks:
            newest_seq = next(reversed(self._chunks))
            if chunk.sequence_id > newest_seq + 1:
                gap = (newest_seq + 1, chunk.sequence_id - 1)
                self._stats.gaps.append(gap)
                raise BufferGapError(f"Sequence gap detected: {gap}")

        # Check memory limit
        if self._total_bytes + len(chunk.payload) > self.max_memory_bytes:
            self._evict_oldest()
            if self._total_bytes + len(chunk.payload) > self.max_memory_bytes:
                raise BufferFullError(f"Buffer exceeds memory limit: {self.max_memory_bytes} bytes")

        # Add chunk
        self._chunks[chunk.sequence_id] = chunk
        self._total_bytes += len(chunk.payload)

        # Evict chunks outside the window
        self._evict_expired()

    def get(self, sequence_id: int) -> Chunk | None:
        """Retrieve a chunk by sequence ID, or None if not present."""
        return self._chunks.get(sequence_id)

    def get_range(self, start: int, end: int) -> list[Chunk]:
        """Retrieve chunks in the inclusive sequence range [start, end]."""
        return [self._chunks[seq] for seq in range(start, end + 1) if seq in self._chunks]

    def get_missing(self, start: int, end: int) -> list[int]:
        """Return sequence IDs in [start, end] that are missing from the buffer."""
        return [seq for seq in range(start, end + 1) if seq not in self._chunks]

    def clear(self) -> None:
        """Clear all chunks from the buffer."""
        self._chunks.clear()
        self._total_bytes = 0
        self._stats = BufferStats(window_seconds=self.window_seconds)

    def __iter__(self) -> Iterator[Chunk]:
        """Iterate over chunks in sequence order."""
        return iter(self._chunks.values())

    def __len__(self) -> int:
        return len(self._chunks)

    def _evict_expired(self) -> None:
        """Evict chunks older than the sliding window."""
        if not self._chunks:
            return

        newest_ts = next(reversed(self._chunks.values())).timestamp
        cutoff = newest_ts - (self.window_seconds * 1000)

        while self._chunks:
            oldest = next(iter(self._chunks.values()))
            if oldest.timestamp >= cutoff:
                break
            self._evict_oldest()

    def _evict_oldest(self) -> None:
        """Evict the oldest chunk from the buffer."""
        if not self._chunks:
            return
        _, chunk = self._chunks.popitem(last=False)
        self._total_bytes -= len(chunk.payload)

    def _update_stats(self) -> None:
        """Refresh the stats object from current buffer state."""
        self._stats.total_chunks = len(self._chunks)
        self._stats.total_bytes = self._total_bytes

        if self._chunks:
            oldest = next(iter(self._chunks.values()))
            newest = next(reversed(self._chunks.values()))
            self._stats.oldest_sequence = oldest.sequence_id
            self._stats.newest_sequence = newest.sequence_id
            self._stats.oldest_timestamp = oldest.timestamp
            self._stats.newest_timestamp = newest.timestamp
        else:
            self._stats.oldest_sequence = None
            self._stats.newest_sequence = None
            self._stats.oldest_timestamp = None
            self._stats.newest_timestamp = None

        # Determine state
        if not self._chunks:
            self._stats.state = BufferState.FILLING
        elif self._stats.fill_ratio >= 0.8:
            self._stats.state = BufferState.HEALTHY
        elif self._stats.fill_ratio < 0.3:
            self._stats.state = BufferState.STALLING
        else:
            self._stats.state = BufferState.FILLING
