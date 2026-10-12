"""Tests for the Q-Tube manifest compatibility mapping.

Validates a representative ``QTubeManifest`` against the invariants documented
in ``docs/qtube-integration.md`` — a fixture stands in for Q-Tube's reader
while its authoritative schema is unconfirmed. When Q-Tube's schema lands,
swap the fixture for it and keep these invariants as the cross-check.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from qlive.archival import ArchivalPipeline, QTubeManifest
from qlive.chunk import create_chunk

HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"qtube-compat").digest()


def make_chunk(stream_id: bytes, seq: int, payload_size: int = 1024) -> object:
    """Create a test chunk with a specific sequence."""
    return create_chunk(
        stream_id,
        seq,
        b"\x00" * payload_size,
        timestamp=seq * 1000,
    )


def build_manifest(stream_id: bytes, **overrides: object) -> dict:
    """Build a full manifest dict, optionally overriding fields."""
    manifest = QTubeManifest(
        stream_id=stream_id,
        publisher="alice",
        title="Compat Stream",
        description="A stream for schema checks",
        category="gaming",
        started_at=1_700_000_000_000,
        ended_at=1_700_003_600_000,
        chunk_hashes=[
            hashlib.sha256(b"chunk-0").hexdigest(),
            hashlib.sha256(b"chunk-1").hexdigest(),
        ],
        total_size=20_971_520,
        fragment_count=3600,
        duration_ms=3_600_000,
        codec="h264",
        resolution="1920x1080",
        fps=30,
        is_partial=False,
    )
    data = manifest.to_dict()
    data.update(overrides)
    return data


class TestManifestDiscriminator:
    def test_type_and_version(self, stream_id):
        data = build_manifest(stream_id)
        assert data["type"] == "qtube-video"
        assert data["version"] == 1

    def test_unknown_type_is_not_qtube_video(self, stream_id):
        data = build_manifest(stream_id, type="something-else")
        assert data["type"] != "qtube-video"


class TestIdentity:
    def test_stream_id_is_lowercase_hex64(self, stream_id):
        data = build_manifest(stream_id)
        assert data["streamId"] == stream_id.hex()
        assert HEX64.match(data["streamId"])

    def test_stream_id_is_64_chars(self, stream_id):
        data = build_manifest(stream_id)
        assert len(data["streamId"]) == 64


class TestChunkHashes:
    def test_hashes_are_sha256_hex(self, stream_id):
        data = build_manifest(stream_id)
        assert len(data["chunkHashes"]) > 0
        for h in data["chunkHashes"]:
            assert HEX64.match(h)

    def test_empty_hashes_rejected(self, stream_id):
        data = build_manifest(stream_id, chunkHashes=[])
        # An empty archive cannot be finalized (pipeline raises), so a manifest
        # with no chunk hashes is not a valid Q-Tube video.
        assert data["chunkHashes"] == []


class TestTimestamps:
    def test_epoch_ms_and_ordering(self, stream_id):
        data = build_manifest(stream_id)
        assert data["startedAt"] > 0
        assert data["endedAt"] >= data["startedAt"]
        # Epoch ms for a plausible recent date (2023-ish and later).
        assert data["startedAt"] >= 1_600_000_000_000

    def test_duration_is_positive(self, stream_id):
        data = build_manifest(stream_id)
        assert data["durationMs"] > 0


class TestJsonTypes:
    def test_numeric_and_bool_types(self, stream_id):
        data = build_manifest(stream_id)
        assert isinstance(data["totalSize"], int)
        assert isinstance(data["fragmentCount"], int)
        assert isinstance(data["durationMs"], int)
        assert isinstance(data["isPartial"], bool)

    def test_is_partial_flag(self, stream_id):
        assert build_manifest(stream_id)["isPartial"] is False
        assert build_manifest(stream_id, isPartial=True)["isPartial"] is True


class TestPartialArchive:
    def test_partial_flags_interrupted_stream(self, stream_id):
        data = build_manifest(stream_id, isPartial=True)
        assert data["isPartial"] is True


class TestSerialization:
    def test_manifest_round_trips_to_json(self, stream_id):
        data = build_manifest(stream_id)
        parsed = json.loads(json.dumps(data))
        assert parsed == data

    def test_to_json_is_valid(self, stream_id):
        manifest = QTubeManifest(
            stream_id=stream_id,
            publisher="alice",
            title="Compat Stream",
        )
        parsed = json.loads(manifest.to_json())
        assert parsed["type"] == "qtube-video"


class TestPipelineManifest:
    def test_pipeline_finalize_satisfies_invariants(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="alice",
            title="Compat Stream",
            min_chunk_bytes=2048,
        )
        for seq in range(1, 7):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        data = pipeline.finalize().to_dict()

        assert data["type"] == "qtube-video"
        assert HEX64.match(data["streamId"])
        assert data["chunkHashes"]
        assert all(HEX64.match(h) for h in data["chunkHashes"])
        assert data["endedAt"] >= data["startedAt"] >= 0
        assert data["durationMs"] > 0
        assert isinstance(data["isPartial"], bool)