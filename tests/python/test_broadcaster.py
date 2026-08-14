"""Tests for the QLive broadcaster application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.broadcaster import (
    Broadcaster,
    BroadcasterConfig,
    BroadcasterError,
    BroadcasterState,
)
from qlive.segmenter import Segment


@pytest.fixture
def private_key() -> ed25519.Ed25519PrivateKey:
    """A fresh Ed25519 private key."""
    return ed25519.Ed25519PrivateKey.generate()


@pytest.fixture
def config() -> BroadcasterConfig:
    """A test broadcaster config."""
    return BroadcasterConfig(
        qortal_name="test-name",
        source="test.mp4",
        title="Test Stream",
        description="A test stream",
        category="tech",
    )


def make_segment(seq: int, data: bytes = b"\x00" * 1024) -> Segment:
    """Create a test segment."""
    return Segment(
        data=data,
        sequence_id=seq,
        timestamp=seq * 1000,
        duration_ms=1000,
    )


class TestBroadcasterConfig:
    def test_defaults(self):
        config = BroadcasterConfig(
            qortal_name="test-name",
            source="test.mp4",
            title="Test Stream",
        )
        assert config.description == ""
        assert config.category == "other"
        assert config.fragment_ms == 1000
        assert config.video_bitrate == "4500k"
        assert config.audio_bitrate == "128k"
        assert config.fps == 30
        assert config.width == 1920
        assert config.height == 1080
        assert config.ffmpeg_path == "ffmpeg"
        assert config.archive_to_vod is True
        assert config.min_archive_chunk_bytes == 10 * 1024 * 1024


class TestBroadcasterInit:
    def test_init(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)
        assert broadcaster.config == config
        assert broadcaster.private_key == private_key
        assert broadcaster.state == BroadcasterState.IDLE
        assert broadcaster.stream_id is None
        assert broadcaster.is_live is False
        assert broadcaster.stats.state == BroadcasterState.IDLE


class TestBroadcasterStart:
    @pytest.mark.asyncio
    async def test_start_success(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await broadcaster.start()

        assert broadcaster.state == BroadcasterState.LIVE
        assert broadcaster.is_live is True
        assert broadcaster.stream_id is not None
        assert broadcaster._registry is not None
        assert broadcaster._swarm is not None
        assert broadcaster._archival is not None
        assert broadcaster._segmenter is not None

    @pytest.mark.asyncio
    async def test_start_idempotent(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await broadcaster.start()
            await broadcaster.start()  # Second call should be no-op

        assert broadcaster.state == BroadcasterState.LIVE
        assert mock_popen.call_count == 1

    @pytest.mark.asyncio
    async def test_start_error(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)

        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            with pytest.raises(BroadcasterError):
                await broadcaster.start()

        assert broadcaster.state == BroadcasterState.ERROR

    @pytest.mark.asyncio
    async def test_start_no_archive(self, config, private_key):
        config.archive_to_vod = False
        broadcaster = Broadcaster(config, private_key)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await broadcaster.start()

        assert broadcaster._archival is None


class TestBroadcasterStop:
    @pytest.mark.asyncio
    async def test_stop(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await broadcaster.start()
            await broadcaster.stop()

        assert broadcaster.state == BroadcasterState.STOPPED
        assert broadcaster._segmenter is not None
        assert broadcaster._segmenter.state.value == "stopped"

    @pytest.mark.asyncio
    async def test_stop_idle(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)
        await broadcaster.stop()  # Should be no-op
        assert broadcaster.state == BroadcasterState.IDLE


class TestProcessSegment:
    def test_process_segment(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)
        broadcaster._stream_id = b"\x00" * 32
        broadcaster._archival = MagicMock()

        segment = make_segment(1)
        broadcaster._process_segment(segment)

        assert broadcaster._sequence == 1
        assert broadcaster.stats.segments_produced == 1
        assert broadcaster.stats.chunks_signed == 1
        assert broadcaster.stats.chunks_distributed == 1
        assert broadcaster.stats.bytes_produced == 1024
        assert broadcaster._archival.add_chunk.called

    def test_process_multiple_segments(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)
        broadcaster._stream_id = b"\x00" * 32
        broadcaster._archival = MagicMock()

        for seq in range(1, 4):
            broadcaster._process_segment(make_segment(seq))

        assert broadcaster._sequence == 3
        assert broadcaster.stats.segments_produced == 3
        assert broadcaster.stats.chunks_signed == 3
        assert broadcaster.stats.bytes_produced == 3072

    def test_process_segment_no_archive(self, config, private_key):
        config.archive_to_vod = False
        broadcaster = Broadcaster(config, private_key)
        broadcaster._stream_id = b"\x00" * 32

        broadcaster._process_segment(make_segment(1))
        assert broadcaster.stats.segments_produced == 1


class TestBroadcasterRun:
    @pytest.mark.asyncio
    async def test_run_processes_segments(self, config, private_key):
        broadcaster = Broadcaster(config, private_key)
        broadcaster._stream_id = b"\x00" * 32
        broadcaster._archival = MagicMock()

        # Mock segmenter to yield 3 segments then stop
        async def mock_segments():
            yield make_segment(1)
            yield make_segment(2)
            yield make_segment(3)

        mock_segmenter = MagicMock()
        mock_segmenter.segments.return_value = mock_segments()
        broadcaster._segmenter = mock_segmenter
        broadcaster.state = BroadcasterState.LIVE

        with patch.object(broadcaster, "stop", new_callable=AsyncMock):
            await broadcaster.run()

        assert broadcaster.stats.segments_produced == 3
        assert broadcaster.stats.chunks_signed == 3
        assert broadcaster.stats.chunks_distributed == 3
