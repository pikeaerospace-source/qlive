"""Tests for the QLive QDN signaling integration."""

import hashlib
import json

import pytest

from qlive.signaling import (
    ArchiveInfo,
    BitrateInfo,
    CodecInfo,
    EncryptionInfo,
    ResolutionInfo,
    SignalingError,
    StreamMetadata,
    StreamNotFoundError,
    StreamRegistry,
    StreamStatus,
    SwarmInfo,
)


def make_metadata(
    publisher: str = "test-name",
    title: str = "Test Stream",
    status: StreamStatus = StreamStatus.ANNOUNCED,
) -> StreamMetadata:
    """Create a test stream metadata."""
    return StreamMetadata(
        publisher=publisher,
        title=title,
        status=status,
    )


class TestStreamMetadata:
    def test_defaults(self):
        metadata = make_metadata()
        assert metadata.publisher == "test-name"
        assert metadata.title == "Test Stream"
        assert metadata.description == ""
        assert metadata.category == "other"
        assert metadata.status == StreamStatus.ANNOUNCED
        assert metadata.fragment_duration_ms == 1000
        assert metadata.version == 1
        assert metadata.codec.video == "h264"
        assert metadata.codec.audio == "aac"
        assert metadata.codec.container == "cmaf"
        assert metadata.resolution.width == 1920
        assert metadata.resolution.height == 1080
        assert metadata.resolution.fps == 30
        assert metadata.bitrate.video == 4500000
        assert metadata.bitrate.audio == 128000
        assert metadata.encryption.enabled is False
        assert metadata.encryption.key_id is None
        assert metadata.swarm.primary_tree == []
        assert metadata.swarm.mesh_peers == []
        assert metadata.archive.status == "pending"

    def test_stream_id_is_sha256(self):
        metadata = make_metadata()
        expected = hashlib.sha256(metadata.to_json().encode()).digest()
        assert metadata.stream_id == expected
        assert len(metadata.stream_id) == 32

    def test_to_dict(self):
        metadata = make_metadata()
        data = metadata.to_dict()
        assert data["type"] == "qlive-stream"
        assert data["publisher"] == "test-name"
        assert data["title"] == "Test Stream"
        assert data["status"] == "announced"
        assert data["codec"]["video"] == "h264"
        assert data["resolution"]["width"] == 1920
        assert data["bitrate"]["video"] == 4500000
        assert data["encryption"]["enabled"] is False
        assert data["swarm"]["primaryTree"] == []
        assert data["archive"]["status"] == "pending"

    def test_to_json_roundtrip(self):
        metadata = make_metadata()
        json_str = metadata.to_json()
        parsed = json.loads(json_str)
        assert parsed["publisher"] == "test-name"
        assert parsed["title"] == "Test Stream"

    def test_from_dict(self):
        data = {
            "publisher": "test-name",
            "title": "Test Stream",
            "description": "A test stream",
            "category": "tech",
            "startedAt": 1234567890,
            "status": "live",
            "fragmentDurationMs": 500,
            "codec": {"video": "av1", "audio": "opus", "container": "fmp4"},
            "resolution": {"width": 1280, "height": 720, "fps": 60},
            "bitrate": {"video": 2000000, "audio": 96000},
            "encryption": {"enabled": True, "keyId": "key-1"},
            "swarm": {"primaryTree": ["node-1"], "meshPeers": ["node-2"]},
            "archive": {
                "status": "in-progress",
                "qdnResourceId": "resource-1",
                "qtubeManifestId": "manifest-1",
            },
            "version": 2,
        }
        metadata = StreamMetadata.from_dict(data)
        assert metadata.publisher == "test-name"
        assert metadata.description == "A test stream"
        assert metadata.category == "tech"
        assert metadata.started_at == 1234567890
        assert metadata.status == StreamStatus.LIVE
        assert metadata.fragment_duration_ms == 500
        assert metadata.codec.video == "av1"
        assert metadata.codec.audio == "opus"
        assert metadata.codec.container == "fmp4"
        assert metadata.resolution.width == 1280
        assert metadata.resolution.height == 720
        assert metadata.resolution.fps == 60
        assert metadata.bitrate.video == 2000000
        assert metadata.bitrate.audio == 96000
        assert metadata.encryption.enabled is True
        assert metadata.encryption.key_id == "key-1"
        assert metadata.swarm.primary_tree == ["node-1"]
        assert metadata.swarm.mesh_peers == ["node-2"]
        assert metadata.archive.status == "in-progress"
        assert metadata.archive.qdn_resource_id == "resource-1"
        assert metadata.archive.qtube_manifest_id == "manifest-1"
        assert metadata.version == 2

    def test_from_dict_missing_required(self):
        with pytest.raises(SignalingError):
            StreamMetadata.from_dict({"title": "Missing publisher"})

    def test_from_json(self):
        metadata = make_metadata()
        json_str = metadata.to_json()
        parsed = StreamMetadata.from_json(json_str)
        assert parsed.publisher == metadata.publisher
        assert parsed.title == metadata.title
        assert parsed.status == metadata.status


class TestStreamRegistry:
    def test_register(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)
        assert len(stream_id) == 32
        assert stream_id.hex() in registry.streams

    def test_unregister(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)
        registry.unregister(stream_id)
        assert stream_id.hex() not in registry.streams

    def test_get(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)
        assert registry.get(stream_id) is metadata

    def test_get_not_found(self):
        registry = StreamRegistry()
        assert registry.get(b"\x00" * 32) is None

    def test_get_by_publisher(self):
        registry = StreamRegistry()
        registry.register(make_metadata(publisher="name-1", title="Stream 1"))
        registry.register(make_metadata(publisher="name-1", title="Stream 2"))
        registry.register(make_metadata(publisher="name-2", title="Stream 3"))

        streams = registry.get_by_publisher("name-1")
        assert len(streams) == 2
        assert all(s.publisher == "name-1" for s in streams)

    def test_get_live(self):
        registry = StreamRegistry()
        registry.register(make_metadata(title="Live 1", status=StreamStatus.LIVE))
        registry.register(make_metadata(title="Live 2", status=StreamStatus.LIVE))
        registry.register(make_metadata(title="Announced"))

        live = registry.get_live()
        assert len(live) == 2
        assert all(s.status == StreamStatus.LIVE for s in live)

    def test_get_announced(self):
        registry = StreamRegistry()
        registry.register(make_metadata(title="Live", status=StreamStatus.LIVE))
        registry.register(make_metadata(title="Announced 1"))
        registry.register(make_metadata(title="Announced 2"))

        announced = registry.get_announced()
        assert len(announced) == 2
        assert all(s.status == StreamStatus.ANNOUNCED for s in announced)

    def test_update_status(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)

        registry.update_status(stream_id, StreamStatus.LIVE)
        assert metadata.status == StreamStatus.LIVE

        registry.update_status(stream_id, StreamStatus.ENDED)
        assert metadata.status == StreamStatus.ENDED

    def test_update_status_not_found(self):
        registry = StreamRegistry()
        with pytest.raises(StreamNotFoundError):
            registry.update_status(b"\x00" * 32, StreamStatus.LIVE)

    def test_update_swarm(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)

        registry.update_swarm(
            stream_id,
            primary_tree=["node-1", "node-2"],
            mesh_peers=["node-3"],
        )
        assert metadata.swarm.primary_tree == ["node-1", "node-2"]
        assert metadata.swarm.mesh_peers == ["node-3"]

    def test_update_swarm_partial(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)

        registry.update_swarm(stream_id, primary_tree=["node-1"])
        assert metadata.swarm.primary_tree == ["node-1"]
        assert metadata.swarm.mesh_peers == []

    def test_update_swarm_not_found(self):
        registry = StreamRegistry()
        with pytest.raises(StreamNotFoundError):
            registry.update_swarm(b"\x00" * 32, primary_tree=["node-1"])

    def test_update_archive(self):
        registry = StreamRegistry()
        metadata = make_metadata()
        stream_id = registry.register(metadata)

        registry.update_archive(
            stream_id,
            status="complete",
            qdn_resource_id="resource-1",
            qtube_manifest_id="manifest-1",
        )
        assert metadata.archive.status == "complete"
        assert metadata.archive.qdn_resource_id == "resource-1"
        assert metadata.archive.qtube_manifest_id == "manifest-1"

    def test_update_archive_not_found(self):
        registry = StreamRegistry()
        with pytest.raises(StreamNotFoundError):
            registry.update_archive(b"\x00" * 32, status="complete")

    def test_clear(self):
        registry = StreamRegistry()
        registry.register(make_metadata())
        registry.register(make_metadata(title="Another"))
        registry.clear()
        assert registry.streams == {}