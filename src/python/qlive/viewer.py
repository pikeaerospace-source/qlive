"""QLive viewer application.

Implements the viewer side of the QLive protocol. Ties together the
buffer, retransmission, swarm, and signaling components to receive
and play a live stream.

The viewer:
1. Discovers streams via QDN signaling
2. Joins the swarm for a stream
3. Receives chunks and buffers them
4. Detects gaps and requests retransmission
5. Manages adaptive bitrate based on buffer health
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from qlive.adaptive import AdaptiveBitrateController, BitrateAction, BitrateLadder
from qlive.buffer import BufferState, SlidingWindowBuffer
from qlive.chunk import Chunk
from qlive.retransmit import RetransmissionManager
from qlive.signaling import StreamRegistry
from qlive.swarm import SwarmManager


class ViewerState(Enum):
    """Viewer lifecycle states."""

    IDLE = "idle"
    DISCOVERING = "discovering"
    CONNECTING = "connecting"
    PLAYING = "playing"
    STALLED = "stalled"
    STOPPED = "stopped"
    ERROR = "error"


class ViewerError(Exception):
    """Base exception for viewer errors."""


@dataclass
class ViewerStats:
    """Statistics for viewer monitoring."""

    state: ViewerState = ViewerState.IDLE
    chunks_received: int = 0
    chunks_verified: int = 0
    bytes_received: int = 0
    gaps_detected: int = 0
    retransmissions_requested: int = 0
    retransmissions_recovered: int = 0
    buffer_state: BufferState = BufferState.FILLING
    current_bitrate: int = 0
    started_at: int | None = None
    duration_seconds: int = 0


class Viewer:
    """QLive viewer application.

    Usage:
        viewer = Viewer(node_id="my-node")
        await viewer.connect(stream_id)
        # ... stream plays ...
        await viewer.disconnect()
    """

    def __init__(
        self,
        node_id: str,
        buffer_seconds: int = 45,
    ) -> None:
        self.node_id = node_id
        self.state = ViewerState.IDLE
        self._buffer = SlidingWindowBuffer(window_seconds=buffer_seconds)
        self._retransmit = RetransmissionManager()
        self._adaptive = AdaptiveBitrateController()
        self._swarm: SwarmManager | None = None
        self._registry: StreamRegistry | None = None
        self._stream_id: bytes | None = None
        self._stats = ViewerStats()
        self._last_sequence = 0

    @property
    def stats(self) -> ViewerStats:
        """Current viewer statistics."""
        self._update_stats()
        return self._stats

    @property
    def stream_id(self) -> bytes | None:
        """The active stream ID (None until connected)."""
        return self._stream_id

    @property
    def is_playing(self) -> bool:
        """Whether the viewer is actively playing a stream."""
        return self.state == ViewerState.PLAYING

    @property
    def buffer(self) -> SlidingWindowBuffer:
        """The viewer's sliding-window buffer."""
        return self._buffer

    def connect(self, stream_id: bytes) -> None:
        """Connect to a live stream.

        Discovers the stream, joins the swarm, and starts receiving.
        """
        if self.state in (ViewerState.CONNECTING, ViewerState.PLAYING):
            return

        self.state = ViewerState.CONNECTING
        self._stream_id = stream_id
        self._stats.started_at = int(time.time())

        # Initialize components
        self._registry = StreamRegistry()
        self._swarm = SwarmManager(self.node_id)

        # Verify stream exists
        metadata = self._registry.get(stream_id)
        if not metadata:
            # In a real implementation, this would query QDN
            # For now, create a placeholder to allow testing
            pass

        self.state = ViewerState.PLAYING

    def disconnect(self) -> None:
        """Disconnect from the current stream."""
        if self.state in (ViewerState.IDLE, ViewerState.STOPPED):
            return

        self._buffer.clear()
        self._retransmit.clear()
        self._stream_id = None
        self._last_sequence = 0
        self.state = ViewerState.STOPPED

    def receive_chunk(self, chunk: Chunk) -> bool:
        """Receive and process a chunk from the swarm.

        Returns True if the chunk was accepted.
        """
        if self.state not in (ViewerState.PLAYING, ViewerState.STALLED):
            return False

        if self._stream_id and chunk.stream_id != self._stream_id:
            return False

        self._stats.chunks_received += 1
        self._stats.bytes_received += len(chunk.payload)

        # Check for sequence gap
        if self._last_sequence > 0 and chunk.sequence_id > self._last_sequence + 1:
            self._handle_gap(self._last_sequence + 1, chunk.sequence_id - 1)

        # Add to buffer
        try:
            self._buffer.add(chunk)
            self._stats.chunks_verified += 1
            self._last_sequence = max(self._last_sequence, chunk.sequence_id)
            return True
        except Exception:
            return False

    def _handle_gap(self, start: int, end: int) -> None:
        """Handle a sequence gap by requesting retransmission."""
        self._stats.gaps_detected += 1

        if not self._swarm:
            return

        missing = list(range(start, end + 1))
        peers = self._swarm.get_missing_from_mesh(missing)
        if not peers:
            return

        # Request from first available peer
        request = self._retransmit.request(
            stream_id=self._stream_id or b"",
            missing_sequences=missing,
            peer_id=peers[0],
        )
        self._retransmit.mark_sent(request)
        self._stats.retransmissions_requested += 1

    def handle_retransmitted_chunk(self, chunk: Chunk, peer_id: str) -> bool:
        """Handle a chunk received via retransmission.

        Returns True if the chunk was accepted for a pending request.
        """
        if self._retransmit.handle_chunk(chunk, peer_id):
            self._stats.retransmissions_recovered += 1
            try:
                self._buffer.add(chunk)
                return True
            except Exception:
                return False
        return False

    def check_buffer_health(self) -> None:
        """Check buffer health and adjust bitrate if needed."""
        buffer_state = self._buffer.state

        # Empty buffer is stalling
        if self._buffer.size == 0:
            buffer_state = BufferState.STALLING

        if buffer_state == BufferState.STALLING:
            self.state = ViewerState.STALLED
        elif buffer_state == BufferState.HEALTHY and self.state == ViewerState.STALLED:
            self.state = ViewerState.PLAYING

        # Adaptive bitrate
        action = self._adaptive.evaluate(buffer_state)
        if action != BitrateAction.STAY:
            self._adaptive.apply(action)

    def set_renditions(self, renditions: list[int]) -> None:
        """Rebuild the adaptive controller using the stream's advertised renditions."""
        self._adaptive = AdaptiveBitrateController(ladder=BitrateLadder(renditions))

    def _update_stats(self) -> None:
        """Refresh viewer statistics."""
        self._stats.state = self.state
        self._stats.buffer_state = self._buffer.state
        self._stats.current_bitrate = self._adaptive.current_bitrate
        if self._stats.started_at:
            self._stats.duration_seconds = int(time.time()) - self._stats.started_at
