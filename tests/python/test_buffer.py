"""Tests for the QLive RAM sliding-window buffer."""

import hashlib

import pytest

from qlive.buffer import (
    DEFAULT_BUFFER_SECONDS,
    MAX_BUFFER_SECONDS,
    MIN_BUFFER_SECONDS,
    BufferError,
    BufferFullError,
    BufferGapError,
    BufferState,
    SlidingWindowBuffer,
)
from qlive.chunk import create_chunk


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"test-stream").digest()


def make_chunk(
    stream_id: bytes,
    seq: int,
    timestamp: int,
    payload_size: int = 1024,
) -> object:
    """Create a test chunk with a specific sequence and timestamp."""
    return create_chunk(
        stream_id,
        seq,
        b"\x00" * payload_size,
        timestamp=timestamp,
    )


class TestBufferInit:
    def test_default_init(self):
        buffer = SlidingWindowBuffer()
        assert buffer.window_seconds == DEFAULT_BUFFER_SECONDS
        assert buffer.size == 0
        assert buffer.memory_usage == 0
        assert buffer.state == BufferState.FILLING

    def test_custom_window(self):
        buffer = SlidingWindowBuffer(window_seconds=30)
        assert buffer.window_seconds == 30

    def test_invalid_window_too_short(self):
        with pytest.raises(BufferError):
            SlidingWindowBuffer(window_seconds=MIN_BUFFER_SECONDS - 1)

    def test_invalid_window_too_long(self):
        with pytest.raises(BufferError):
            SlidingWindowBuffer(window_seconds=MAX_BUFFER_SECONDS + 1)


class TestBufferAdd:
    def test_add_single_chunk(self, stream_id):
        buffer = SlidingWindowBuffer()
        chunk = make_chunk(stream_id, 1, 1000)
        buffer.add(chunk)
        assert buffer.size == 1
        assert buffer.memory_usage == len(chunk.payload)
        assert buffer.get(1) is chunk

    def test_add_sequential_chunks(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 11):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        assert buffer.size == 10
        assert buffer.get(5) is not None

    def test_add_out_of_order(self, stream_id):
        buffer = SlidingWindowBuffer()
        buffer.add(make_chunk(stream_id, 1, 1000))
        buffer.add(make_chunk(stream_id, 2, 2000))
        buffer.add(make_chunk(stream_id, 3, 3000))
        assert buffer.size == 3

    def test_add_duplicate_sequence(self, stream_id):
        buffer = SlidingWindowBuffer()
        chunk1 = make_chunk(stream_id, 1, 1000)
        chunk2 = make_chunk(stream_id, 1, 1000)
        buffer.add(chunk1)
        buffer.add(chunk2)
        assert buffer.size == 1
        assert buffer.get(1) is chunk2  # Latest wins

    def test_add_gap_detection(self, stream_id):
        buffer = SlidingWindowBuffer()
        buffer.add(make_chunk(stream_id, 1, 1000))
        with pytest.raises(BufferGapError):
            buffer.add(make_chunk(stream_id, 3, 3000))
        assert buffer.size == 1  # Gap chunk not added

    def test_add_memory_limit(self, stream_id):
        buffer = SlidingWindowBuffer(max_memory_bytes=2048)
        buffer.add(make_chunk(stream_id, 1, 1000, payload_size=1024))
        buffer.add(make_chunk(stream_id, 2, 2000, payload_size=1024))
        # Third chunk would exceed 2048 bytes, oldest is evicted
        buffer.add(make_chunk(stream_id, 3, 3000, payload_size=1024))
        assert buffer.size == 2
        assert buffer.get(1) is None  # Evicted
        assert buffer.get(2) is not None
        assert buffer.get(3) is not None


class TestBufferEviction:
    def test_evict_expired(self, stream_id):
        buffer = SlidingWindowBuffer(window_seconds=30)
        # Add chunks spanning 60 seconds
        for seq in range(1, 61):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))

        # Oldest chunks (first 29s) should be evicted
        # Chunk 30 (ts=30000) is exactly at the cutoff and is kept
        assert buffer.get(1) is None
        assert buffer.get(15) is None
        assert buffer.get(29) is None
        assert buffer.get(30) is not None
        assert buffer.get(60) is not None
        assert buffer.size == 31

    def test_evict_oldest_first(self, stream_id):
        buffer = SlidingWindowBuffer(window_seconds=30)
        for seq in range(1, 61):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))

        # Verify oldest remaining is seq 30 (at the cutoff boundary)
        assert buffer.stats.oldest_sequence == 30
        assert buffer.stats.newest_sequence == 60

    def test_clear(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 6):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        buffer.clear()
        assert buffer.size == 0
        assert buffer.memory_usage == 0
        assert buffer.state == BufferState.FILLING


class TestBufferRetrieval:
    def test_get_missing(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in [1, 2, 4, 5]:
            try:
                buffer.add(make_chunk(stream_id, seq, seq * 1000))
            except BufferGapError:
                pass  # Gap detected, chunk not added
        assert buffer.get(3) is None
        assert buffer.get(4) is None  # Not added due to gap
        assert buffer.get(5) is None  # Not added due to gap

    def test_get_range(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 11):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        chunks = buffer.get_range(3, 7)
        assert len(chunks) == 5
        assert [c.sequence_id for c in chunks] == [3, 4, 5, 6, 7]

    def test_get_missing_range(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in [1, 2, 4, 5]:
            try:
                buffer.add(make_chunk(stream_id, seq, seq * 1000))
            except BufferGapError:
                pass  # Gap detected, chunk not added
        missing = buffer.get_missing(1, 5)
        assert missing == [3, 4, 5]

    def test_iteration_order(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 6):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        sequences = [c.sequence_id for c in buffer]
        assert sequences == [1, 2, 3, 4, 5]

    def test_len(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 6):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        assert len(buffer) == 5


class TestBufferStats:
    def test_stats_empty(self):
        buffer = SlidingWindowBuffer()
        stats = buffer.stats
        assert stats.total_chunks == 0
        assert stats.total_bytes == 0
        assert stats.oldest_sequence is None
        assert stats.newest_sequence is None
        assert stats.state == BufferState.FILLING
        assert stats.fill_ratio == 0.0

    def test_stats_with_chunks(self, stream_id):
        buffer = SlidingWindowBuffer()
        for seq in range(1, 11):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        stats = buffer.stats
        assert stats.total_chunks == 10
        assert stats.oldest_sequence == 1
        assert stats.newest_sequence == 10

    def test_stats_healthy_state(self, stream_id):
        buffer = SlidingWindowBuffer(window_seconds=30)
        # Fill 30 seconds of chunks
        for seq in range(1, 31):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        assert buffer.state == BufferState.HEALTHY

    def test_stats_stalling_state(self, stream_id):
        buffer = SlidingWindowBuffer(window_seconds=30)
        # Only 5 seconds of data
        for seq in range(1, 6):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        assert buffer.state == BufferState.STALLING

    def test_stats_filling_state(self, stream_id):
        buffer = SlidingWindowBuffer(window_seconds=30)
        # 15 seconds of data (50% fill)
        for seq in range(1, 16):
            buffer.add(make_chunk(stream_id, seq, seq * 1000))
        assert buffer.state == BufferState.FILLING

    def test_gap_tracking(self, stream_id):
        buffer = SlidingWindowBuffer()
        buffer.add(make_chunk(stream_id, 1, 1000))
        with pytest.raises(BufferGapError):
            buffer.add(make_chunk(stream_id, 5, 5000))
        assert buffer.stats.gaps == [(2, 4)]