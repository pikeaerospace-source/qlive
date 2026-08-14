"""Tests for the QLive chunk retransmission protocol."""

import hashlib
import time

import pytest

from qlive.chunk import create_chunk
from qlive.retransmit import (
    RetransmitError,
    RetransmitRequest,
    RetransmitState,
    RetransmitStats,
    RetransmissionManager,
)


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"test-stream").digest()


def make_chunk(stream_id: bytes, seq: int) -> object:
    """Create a test chunk with a specific sequence."""
    return create_chunk(stream_id, seq, b"\x00" * 100, timestamp=seq * 1000)


class TestRetransmitRequest:
    def test_init(self, stream_id):
        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=[3, 4, 5],
            peer_id="peer-1",
        )
        assert request.state == RetransmitState.PENDING
        assert request.missing_count == 3
        assert request.received_count == 0
        assert request.is_complete is False
        assert request.attempts == 0
        assert request.max_attempts == 3

    def test_is_expired(self, stream_id):
        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=[3],
            peer_id="peer-1",
            timeout_ms=100,
        )
        assert request.is_expired is False
        # Simulate time passing
        request.created_at = int(time.time() * 1000) - 200
        assert request.is_expired is True

    def test_add_expected_chunk(self, stream_id):
        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=[3, 4],
            peer_id="peer-1",
        )
        chunk = make_chunk(stream_id, 3)
        assert request.add_chunk(chunk) is True
        assert request.received_count == 1
        assert request.missing_sequences == [4]
        assert request.is_complete is False

    def test_add_unexpected_chunk(self, stream_id):
        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=[3],
            peer_id="peer-1",
        )
        chunk = make_chunk(stream_id, 99)
        assert request.add_chunk(chunk) is False
        assert request.received_count == 0

    def test_complete_when_all_received(self, stream_id):
        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=[3, 4],
            peer_id="peer-1",
        )
        request.add_chunk(make_chunk(stream_id, 3))
        assert request.is_complete is False
        request.add_chunk(make_chunk(stream_id, 4))
        assert request.is_complete is True
        assert request.state == RetransmitState.COMPLETE


class TestRetransmitStats:
    def test_init(self):
        stats = RetransmitStats()
        assert stats.total_requests == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.timed_out == 0
        assert stats.total_chunks_recovered == 0
        assert stats.total_chunks_missed == 0
        assert stats.active_requests == 0
        assert stats.success_rate == 0.0

    def test_success_rate(self):
        stats = RetransmitStats(total_requests=10, completed=7)
        assert stats.success_rate == 70.0


class TestRetransmissionManager:
    def test_init(self):
        manager = RetransmissionManager()
        assert manager.default_timeout_ms == 2000
        assert manager.max_attempts == 3
        assert manager.active_requests == []
        assert manager.stats.total_requests == 0

    def test_request(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3, 4, 5], "peer-1")
        assert request.state == RetransmitState.PENDING
        assert request.peer_id == "peer-1"
        assert manager.stats.total_requests == 1
        assert len(manager.active_requests) == 1

    def test_request_empty_sequences(self, stream_id):
        manager = RetransmissionManager()
        with pytest.raises(RetransmitError):
            manager.request(stream_id, [], "peer-1")

    def test_request_deduplication(self, stream_id):
        manager = RetransmissionManager()
        req1 = manager.request(stream_id, [3, 4], "peer-1")
        req2 = manager.request(stream_id, [3, 4], "peer-1")
        assert req1 is req2
        assert manager.stats.total_requests == 1

    def test_mark_sent(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)
        assert request.state == RetransmitState.IN_FLIGHT
        assert request.attempts == 1

    def test_handle_chunk_matching_request(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3, 4], "peer-1")
        manager.mark_sent(request)

        chunk = make_chunk(stream_id, 3)
        assert manager.handle_chunk(chunk, "peer-1") is True
        assert manager.stats.total_chunks_recovered == 1
        assert request.received_count == 1

    def test_handle_chunk_wrong_peer(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        chunk = make_chunk(stream_id, 3)
        assert manager.handle_chunk(chunk, "peer-2") is False
        assert manager.stats.total_chunks_recovered == 0

    def test_handle_chunk_wrong_stream(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        other_stream = hashlib.sha256(b"other-stream").digest()
        chunk = make_chunk(other_stream, 3)
        assert manager.handle_chunk(chunk, "peer-1") is False

    def test_handle_chunk_unexpected_sequence(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        chunk = make_chunk(stream_id, 99)
        assert manager.handle_chunk(chunk, "peer-1") is False

    def test_complete_request(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3, 4], "peer-1")
        manager.mark_sent(request)

        manager.handle_chunk(make_chunk(stream_id, 3), "peer-1")
        manager.handle_chunk(make_chunk(stream_id, 4), "peer-1")

        assert request.state == RetransmitState.COMPLETE
        assert request.is_complete is True
        assert len(manager.active_requests) == 0

    def test_check_timeouts_retry(self, stream_id):
        manager = RetransmissionManager(default_timeout_ms=100, max_attempts=3)
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        # Simulate timeout
        request.created_at = int(time.time() * 1000) - 200
        timed_out = manager.check_timeouts()

        assert len(timed_out) == 0  # Should retry, not timeout
        assert request.state == RetransmitState.PENDING
        assert request.attempts == 1

    def test_check_timeouts_exhausted(self, stream_id):
        manager = RetransmissionManager(default_timeout_ms=100, max_attempts=1)
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        # Simulate timeout
        request.created_at = int(time.time() * 1000) - 200
        timed_out = manager.check_timeouts()

        assert len(timed_out) == 1
        assert request.state == RetransmitState.TIMEOUT
        assert manager.stats.timed_out == 1
        assert manager.stats.total_chunks_missed == 1

    def test_fail_request(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)

        manager.fail(request)
        assert request.state == RetransmitState.FAILED
        assert manager.stats.failed == 1
        assert manager.stats.total_chunks_missed == 1

    def test_fail_completed_request(self, stream_id):
        manager = RetransmissionManager()
        request = manager.request(stream_id, [3], "peer-1")
        manager.mark_sent(request)
        manager.handle_chunk(make_chunk(stream_id, 3), "peer-1")

        manager.fail(request)  # Should be no-op
        assert request.state == RetransmitState.COMPLETE
        assert manager.stats.failed == 0

    def test_clear(self, stream_id):
        manager = RetransmissionManager()
        manager.request(stream_id, [3], "peer-1")
        manager.clear()
        assert manager.active_requests == []
        assert manager.stats.total_requests == 0

    def test_stats_active_requests(self, stream_id):
        manager = RetransmissionManager()
        manager.request(stream_id, [3], "peer-1")
        manager.request(stream_id, [5], "peer-2")
        assert manager.stats.active_requests == 2