"""Tests for the QLive CMAF/fMP4 segmenter."""

import asyncio
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qlive.chunk import MAX_FRAGMENT_MS, MIN_FRAGMENT_MS
from qlive.segmenter import (
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_FPS,
    DEFAULT_FRAGMENT_MS,
    DEFAULT_HEIGHT,
    DEFAULT_VIDEO_BITRATE,
    DEFAULT_WIDTH,
    Segment,
    Segmenter,
    SegmenterConfig,
    SegmenterError,
    SegmenterState,
)


class TestSegmenterConfig:
    def test_default_config(self):
        config = SegmenterConfig(source="rtmp://localhost/live")
        assert config.fragment_ms == DEFAULT_FRAGMENT_MS
        assert config.video_bitrate == DEFAULT_VIDEO_BITRATE
        assert config.audio_bitrate == DEFAULT_AUDIO_BITRATE
        assert config.fps == DEFAULT_FPS
        assert config.width == DEFAULT_WIDTH
        assert config.height == DEFAULT_HEIGHT
        assert config.ffmpeg_path == "ffmpeg"
        assert config.extra_args == []

    def test_custom_config(self):
        config = SegmenterConfig(
            source="test.mp4",
            fragment_ms=500,
            video_bitrate="2000k",
            width=1280,
            height=720,
            extra_args=["-threads", "4"],
        )
        assert config.fragment_ms == 500
        assert config.video_bitrate == "2000k"
        assert config.width == 1280
        assert config.height == 720
        assert config.extra_args == ["-threads", "4"]

    def test_invalid_fragment_too_short(self):
        with pytest.raises(SegmenterError):
            SegmenterConfig(source="test", fragment_ms=MIN_FRAGMENT_MS - 1)

    def test_invalid_fragment_too_long(self):
        with pytest.raises(SegmenterError):
            SegmenterConfig(source="test", fragment_ms=MAX_FRAGMENT_MS + 1)


class TestSegment:
    def test_segment_properties(self):
        segment = Segment(
            data=b"\x00" * 100,
            sequence_id=1,
            timestamp=1000,
            duration_ms=1000,
            is_keyframe=True,
        )
        assert segment.size == 100
        assert segment.sequence_id == 1
        assert segment.timestamp == 1000
        assert segment.duration_ms == 1000
        assert segment.is_keyframe is True

    def test_segment_default_keyframe(self):
        segment = Segment(data=b"data", sequence_id=1, timestamp=0, duration_ms=500)
        assert segment.is_keyframe is False


class TestSegmenterInit:
    def test_init_state(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)
        assert segmenter.state == SegmenterState.IDLE
        assert segmenter.sequence_id == 1
        assert segmenter.is_running is False

    def test_repr(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)
        assert "Segmenter(" in repr(segmenter)
        assert "source='test.mp4'" in repr(segmenter)
        assert "state=idle" in repr(segmenter)


class TestBuildCommand:
    def test_command_structure(self):
        config = SegmenterConfig(source="rtmp://localhost/live")
        segmenter = Segmenter(config)
        segmenter._temp_dir = MagicMock()
        segmenter._temp_dir.name = "/tmp/qlive-test"

        cmd = segmenter._build_command()

        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert "rtmp://localhost/live" in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-preset" in cmd
        assert "veryfast" in cmd
        assert "-tune" in cmd
        assert "zerolatency" in cmd
        assert "-b:v" in cmd
        assert DEFAULT_VIDEO_BITRATE in cmd
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-b:a" in cmd
        assert DEFAULT_AUDIO_BITRATE in cmd
        assert "-f" in cmd
        assert "fmp4" in cmd
        assert "-movflags" in cmd
        assert "frag_keyframe+empty_moov+default_base_moof" in cmd
        assert "-frag_duration" in cmd
        assert str(DEFAULT_FRAGMENT_MS * 1000) in cmd
        assert "-r" in cmd
        assert str(DEFAULT_FPS) in cmd
        assert "-s" in cmd
        assert f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}" in cmd
        assert cmd[-1] == "/tmp/qlive-test/seg_%05d.m4s"

    def test_command_with_extra_args(self):
        config = SegmenterConfig(
            source="test.mp4", extra_args=["-threads", "4", "-g", "60"]
        )
        segmenter = Segmenter(config)
        segmenter._temp_dir = MagicMock()
        segmenter._temp_dir.name = "/tmp/qlive-test"

        cmd = segmenter._build_command()
        assert "-threads" in cmd
        assert "4" in cmd
        assert "-g" in cmd
        assert "60" in cmd

    def test_command_custom_fragment(self):
        config = SegmenterConfig(source="test.mp4", fragment_ms=500)
        segmenter = Segmenter(config)
        segmenter._temp_dir = MagicMock()
        segmenter._temp_dir.name = "/tmp/qlive-test"

        cmd = segmenter._build_command()
        assert "500000" in cmd  # 500ms in microseconds


class TestSegmenterStartStop:
    @pytest.mark.asyncio
    async def test_start_success(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await segmenter.start()

        assert segmenter.state == SegmenterState.RUNNING
        assert segmenter.is_running is True
        assert segmenter._process is not None
        assert segmenter._temp_dir is not None

    @pytest.mark.asyncio
    async def test_start_ffmpeg_not_found(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)

        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            with pytest.raises(SegmenterError):
                await segmenter.start()

        assert segmenter.state == SegmenterState.ERROR

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await segmenter.start()
            await segmenter.start()  # Second call should be no-op

        assert segmenter.state == SegmenterState.RUNNING
        assert mock_popen.call_count == 1

    @pytest.mark.asyncio
    async def test_stop(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            await segmenter.start()
            await segmenter.stop()

        assert segmenter.state == SegmenterState.STOPPED
        assert segmenter._process is None
        assert segmenter._temp_dir is None

    @pytest.mark.asyncio
    async def test_stop_idle(self):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)
        await segmenter.stop()  # Should be no-op
        assert segmenter.state == SegmenterState.IDLE


class TestSegments:
    @pytest.mark.asyncio
    async def test_yields_segments(self, tmp_path):
        config = SegmenterConfig(source="test.mp4", fragment_ms=1000)
        segmenter = Segmenter(config)

        # Create real segment files in a temp directory
        seg1 = tmp_path / "seg_00001.m4s"
        seg2 = tmp_path / "seg_00002.m4s"
        seg1.write_bytes(b"segment-1-data")
        seg2.write_bytes(b"segment-2-data")

        segmenter._temp_dir = type(
            "TempDir", (), {"name": str(tmp_path), "cleanup": lambda self: None}
        )()
        segmenter._start_time = 1000
        segmenter.state = SegmenterState.RUNNING

        # Collect first two segments then stop
        segments = []
        async for segment in segmenter.segments():
            segments.append(segment)
            if len(segments) >= 2:
                segmenter.state = SegmenterState.STOPPED

        assert len(segments) == 2
        assert segments[0].sequence_id == 1
        assert segments[0].data == b"segment-1-data"
        assert segments[0].timestamp == 1000
        assert segments[0].duration_ms == 1000
        assert segments[1].sequence_id == 2
        assert segments[1].data == b"segment-2-data"
        assert segments[1].timestamp == 2000

    @pytest.mark.asyncio
    async def test_skips_empty_segments(self, tmp_path):
        config = SegmenterConfig(source="test.mp4")
        segmenter = Segmenter(config)

        # One empty file, one with data
        seg1 = tmp_path / "seg_00001.m4s"
        seg2 = tmp_path / "seg_00002.m4s"
        seg1.write_bytes(b"")
        seg2.write_bytes(b"real-data")

        segmenter._temp_dir = type(
            "TempDir", (), {"name": str(tmp_path), "cleanup": lambda self: None}
        )()
        segmenter._start_time = 1000
        segmenter.state = SegmenterState.RUNNING

        segments = []
        async for segment in segmenter.segments():
            segments.append(segment)
            if len(segments) >= 1:
                segmenter.state = SegmenterState.STOPPED

        assert len(segments) == 1
        assert segments[0].data == b"real-data"
        assert segments[0].sequence_id == 1
