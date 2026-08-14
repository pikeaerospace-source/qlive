"""QLive chunk retransmission protocol.

Implements the retransmission request protocol for missing chunks
(protocol spec section 5.5, step 4). When a viewer detects a sequence
gap, it requests the missing chunks from its mesh peers.

The protocol uses a simple request/response model over the ephemeral
mesh. Requests are sent to mesh peers, and peers respond with the
requested chunks if they have them in their sliding-window buffer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from qlive.chunk import Chunk


class RetransmitError(Exception):
    """Base exception for retransmission errors."""


class RetransmitState(Enum):
    """Retransmission request lifecycle states."""

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    COMPLETE = "complete"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class RetransmitRequest:
    """A request for missing chunks from a peer."""

    stream_id: bytes
    missing_sequences: list[int]
    peer_id: str
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    timeout_ms: int = 2000
    state: RetransmitState = RetransmitState.PENDING
    received_chunks: list[Chunk] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    _total_missing: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._total_missing = len(self.missing_sequences)

    @property
    def is_expired(self) -> bool:
        """Whether the request has exceeded its timeout."""
        return int(time.time() * 1000) - self.created_at > self.timeout_ms

    @property
    def missing_count(self) -> int:
        """Number of missing sequences still outstanding."""
        return len(self.missing_sequences)

    @property
    def total_missing(self) -> int:
        """Total number of sequences originally requested."""
        return self._total_missing

    @property
    def received_count(self) -> int:
        """Number of chunks received for this request."""
        return len(self.received_chunks)

    @property
    def is_complete(self) -> bool:
        """Whether all requested chunks have been received."""
        return self.received_count >= self._total_missing

    def add_chunk(self, chunk: Chunk) -> bool:
        """Add a received chunk to the request.

        Returns True if the chunk was expected (in the missing list).
        """
        if chunk.sequence_id not in self.missing_sequences:
            return False
        self.received_chunks.append(chunk)
        self.missing_sequences.remove(chunk.sequence_id)
        if self.is_complete:
            self.state = RetransmitState.COMPLETE
        return True


@dataclass
class RetransmitStats:
    """Statistics for retransmission monitoring."""

    total_requests: int = 0
    completed: int = 0
    failed: int = 0
    timed_out: int = 0
    total_chunks_recovered: int = 0
    total_chunks_missed: int = 0
    active_requests: int = 0

    @property
    def success_rate(self) -> float:
        """Percentage of requests that completed successfully."""
        if self.total_requests == 0:
            return 0.0
        return (self.completed / self.total_requests) * 100.0


class RetransmissionManager:
    """Manages retransmission requests for missing chunks.

    Tracks pending requests, handles timeouts, and provides statistics
    for monitoring retransmission health.
    """

    def __init__(
        self,
        default_timeout_ms: int = 2000,
        max_attempts: int = 3,
    ) -> None:
        self.default_timeout_ms = default_timeout_ms
        self.max_attempts = max_attempts
        self._requests: dict[str, RetransmitRequest] = {}
        self._stats = RetransmitStats()

    @property
    def stats(self) -> RetransmitStats:
        """Current retransmission statistics."""
        self._update_stats()
        return self._stats

    @property
    def active_requests(self) -> list[RetransmitRequest]:
        """List of active (pending/in-flight) requests."""
        return [
            req
            for req in self._requests.values()
            if req.state in (RetransmitState.PENDING, RetransmitState.IN_FLIGHT)
        ]

    def request(
        self,
        stream_id: bytes,
        missing_sequences: list[int],
        peer_id: str,
        timeout_ms: int | None = None,
    ) -> RetransmitRequest:
        """Create a new retransmission request for missing chunks.

        Args:
            stream_id: The stream the chunks belong to.
            missing_sequences: List of missing sequence IDs.
            peer_id: The peer to request chunks from.
            timeout_ms: Optional custom timeout (defaults to manager default).

        Returns:
            The created RetransmitRequest.
        """
        if not missing_sequences:
            raise RetransmitError("Cannot request empty sequence list")

        request_id = self._make_request_id(stream_id, peer_id, missing_sequences)

        # If a request already exists for these sequences, return it
        if request_id in self._requests:
            existing = self._requests[request_id]
            if existing.state in (RetransmitState.PENDING, RetransmitState.IN_FLIGHT):
                return existing

        request = RetransmitRequest(
            stream_id=stream_id,
            missing_sequences=sorted(missing_sequences),
            peer_id=peer_id,
            timeout_ms=timeout_ms or self.default_timeout_ms,
            max_attempts=self.max_attempts,
        )
        self._requests[request_id] = request
        self._stats.total_requests += 1
        return request

    def mark_sent(self, request: RetransmitRequest) -> None:
        """Mark a request as sent (in-flight)."""
        request.state = RetransmitState.IN_FLIGHT
        request.attempts += 1

    def handle_chunk(self, chunk: Chunk, peer_id: str) -> bool:
        """Handle an incoming chunk from a peer.

        Returns True if the chunk was accepted for a pending request.
        """
        for request in self._requests.values():
            if (
                request.stream_id == chunk.stream_id
                and request.peer_id == peer_id
                and request.state in (RetransmitState.PENDING, RetransmitState.IN_FLIGHT)
                and request.add_chunk(chunk)
            ):
                self._stats.total_chunks_recovered += 1
                return True
        return False

    def check_timeouts(self) -> list[RetransmitRequest]:
        """Check for expired requests and mark them as timed out.

        Returns the list of requests that timed out.
        """
        timed_out: list[RetransmitRequest] = []
        for request in self._requests.values():
            if (
                request.state in (RetransmitState.PENDING, RetransmitState.IN_FLIGHT)
                and request.is_expired
            ):
                if request.attempts < request.max_attempts:
                    # Retry
                    request.state = RetransmitState.PENDING
                    request.created_at = int(time.time() * 1000)
                else:
                    request.state = RetransmitState.TIMEOUT
                    self._stats.timed_out += 1
                    self._stats.total_chunks_missed += request.missing_count
                    timed_out.append(request)
        return timed_out

    def fail(self, request: RetransmitRequest) -> None:
        """Mark a request as failed."""
        if request.state not in (RetransmitState.COMPLETE, RetransmitState.TIMEOUT):
            request.state = RetransmitState.FAILED
            self._stats.failed += 1
            self._stats.total_chunks_missed += request.missing_count

    def clear(self) -> None:
        """Clear all requests and reset statistics."""
        self._requests.clear()
        self._stats = RetransmitStats()

    def _make_request_id(self, stream_id: bytes, peer_id: str, sequences: list[int]) -> str:
        """Create a unique request ID."""
        seq_str = ",".join(str(s) for s in sorted(sequences))
        return f"{stream_id.hex()}:{peer_id}:{seq_str}"

    def _update_stats(self) -> None:
        """Refresh statistics from current state."""
        self._stats.active_requests = len(self.active_requests)
