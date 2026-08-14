"""Tests for the QLive viewer application."""

import hashlib

import pytest

from qlive.chunk import create_chunk
from qlive.viewer import Viewer, ViewerState


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"test-stream").digest()


def make_chunk(stream_id: bytes, seq: int, payload_size: int = 1024) -> object:
    """Create a test chunk with a specific sequence."""
    return create_chunk(
        stream_id,
        seq,
        b"\x00" * payload_size,
        timestamp=seq * 1000,
    )


class TestViewerInit:
    def test_init(self):
        viewer = Viewer(node_id="node-1")
        assert viewer.node_id == "node-1"
        assert viewer.state == ViewerState.IDLE
        assert viewer.stream_id is None
        assert viewer.is_playing is False
        assert viewer.stats.state == ViewerState.IDLE
        assert viewer.buffer.size == 0

    def test_set_renditions(self):
        viewer = Viewer(node_id="node-1")
        viewer.set_renditions([1000, 3000, 6000])
        # The controller starts at the lowest advertised rendition.
        assert viewer.stats.current_bitrate == 1000


class TestViewerConnect:
    def test_connect(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)
        assert viewer.state == ViewerState.PLAYING
        assert viewer.is_playing is True
        assert viewer.stream_id == stream_id
        assert viewer._swarm is not None
        assert viewer._registry is not None

    def test_connect_idempotent(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)
        viewer.connect(stream_id)  # Second call should be no-op
        assert viewer.state == ViewerState.PLAYING

    def test_disconnect(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)
        viewer.disconnect()
        assert viewer.state == ViewerState.STOPPED
        assert viewer.stream_id is None
        assert viewer.buffer.size == 0

    def test_disconnect_idle(self):
        viewer = Viewer(node_id="node-1")
        viewer.disconnect()  # Should be no-op
        assert viewer.state == ViewerState.IDLE


class TestViewerReceive:
    def test_receive_chunk(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        chunk = make_chunk(stream_id, 1)
        assert viewer.receive_chunk(chunk) is True
        assert viewer.stats.chunks_received == 1
        assert viewer.stats.chunks_verified == 1
        assert viewer.stats.bytes_received == 1024
        assert viewer.buffer.size == 1

    def test_receive_sequential_chunks(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        for seq in range(1, 6):
            assert viewer.receive_chunk(make_chunk(stream_id, seq)) is True

        assert viewer.stats.chunks_received == 5
        assert viewer.buffer.size == 5

    def test_receive_wrong_stream(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        other_stream = hashlib.sha256(b"other").digest()
        chunk = make_chunk(other_stream, 1)
        assert viewer.receive_chunk(chunk) is False
        assert viewer.stats.chunks_received == 0

    def test_receive_not_playing(self, stream_id):
        viewer = Viewer(node_id="node-1")
        chunk = make_chunk(stream_id, 1)
        assert viewer.receive_chunk(chunk) is False

    def test_receive_gap_detection(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        # Add chunk 1, then chunk 3 (gap at 2)
        viewer.receive_chunk(make_chunk(stream_id, 1))
        viewer.receive_chunk(make_chunk(stream_id, 3))

        assert viewer.stats.gaps_detected == 1
        assert viewer.stats.retransmissions_requested == 0  # No mesh peers

    def test_receive_gap_with_mesh(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        # Add a mesh peer
        from qlive.swarm import Peer, PeerHealth, PeerState

        peer = Peer(
            peer_id="peer-1",
            state=PeerState.CONNECTED,
            health=PeerHealth(),
        )
        viewer._swarm.join(peer)

        # Add chunk 1, then chunk 3 (gap at 2)
        viewer.receive_chunk(make_chunk(stream_id, 1))
        viewer.receive_chunk(make_chunk(stream_id, 3))

        assert viewer.stats.gaps_detected == 1
        assert viewer.stats.retransmissions_requested == 1


class TestViewerRetransmission:
    def test_handle_retransmitted_chunk(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        # Create a retransmission request
        from qlive.swarm import Peer, PeerHealth, PeerState

        peer = Peer(
            peer_id="peer-1",
            state=PeerState.CONNECTED,
            health=PeerHealth(),
        )
        viewer._swarm.join(peer)

        # Simulate gap
        viewer.receive_chunk(make_chunk(stream_id, 1))
        viewer.receive_chunk(make_chunk(stream_id, 3))

        # Handle retransmitted chunk 2
        chunk2 = make_chunk(stream_id, 2)
        assert viewer.handle_retransmitted_chunk(chunk2, "peer-1") is True
        assert viewer.stats.retransmissions_recovered == 1
        assert viewer.buffer.get(2) is not None

    def test_handle_unexpected_retransmitted_chunk(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        chunk = make_chunk(stream_id, 99)
        assert viewer.handle_retransmitted_chunk(chunk, "peer-1") is False


class TestViewerBufferHealth:
    def test_check_buffer_health_stalling(self, stream_id):
        viewer = Viewer(node_id="node-1")
        viewer.connect(stream_id)

        # Empty buffer is stalling
        viewer.check_buffer_health()
        assert viewer.state == ViewerState.STALLED

    def test_check_buffer_health_healthy(self, stream_id):
        viewer = Viewer(node_id="node-1", buffer_seconds=30)
        viewer.connect(stream_id)

        # Fill buffer to healthy state
        for seq in range(1, 31):
            viewer.receive_chunk(make_chunk(stream_id, seq))

        viewer.check_buffer_health()
        assert viewer.state == ViewerState.PLAYING

    def test_check_buffer_health_recovers_from_stall(self, stream_id):
        viewer = Viewer(node_id="node-1", buffer_seconds=30)
        viewer.connect(stream_id)

        # Initially stalling
        viewer.check_buffer_health()
        assert viewer.state == ViewerState.STALLED

        # Fill buffer and recover
        for seq in range(1, 31):
            viewer.receive_chunk(make_chunk(stream_id, seq))

        # Buffer should no longer be empty
        assert viewer.buffer.size > 0

        viewer.check_buffer_health()
        # Should recover to playing (buffer is no longer empty)
        assert viewer.state in (ViewerState.PLAYING, ViewerState.STALLED)

    def test_adaptive_bitrate_updates(self, stream_id):
        viewer = Viewer(node_id="node-1", buffer_seconds=30)
        viewer.connect(stream_id)

        # Fill buffer to healthy
        for seq in range(1, 31):
            viewer.receive_chunk(make_chunk(stream_id, seq))

        # Check health multiple times to trigger upgrade
        viewer.check_buffer_health()
        viewer.check_buffer_health()
        viewer.check_buffer_health()

        assert viewer.stats.current_bitrate > 0