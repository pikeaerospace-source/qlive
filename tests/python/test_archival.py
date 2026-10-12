"""Tests for the QLive Live → VOD archival pipeline."""

import hashlib

import pytest

from qlive.archival import (
    QDN_CHUNK_MAX_BYTES,
    QDN_CHUNK_MIN_BYTES,
    ArchiveState,
    ArchivalError,
    ArchivalPipeline,
    QDNDataChunk,
    QTubeManifest,
)
from qlive.chunk import create_chunk


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


class TestQDNDataChunk:
    def test_hash(self):
        chunk = QDNDataChunk(
            index=0,
            data=b"test-data",
            previous_hash=b"\x00" * 32,
        )
        expected = hashlib.sha256(
            (0).to_bytes(8, "big") + b"\x00" * 32 + b"test-data"
        ).digest()
        assert chunk.hash == expected

    def test_size(self):
        chunk = QDNDataChunk(
            index=0,
            data=b"test-data",
            previous_hash=b"\x00" * 32,
        )
        assert chunk.size == 9

    def test_hash_chain_linking(self):
        chunk1 = QDNDataChunk(
            index=0,
            data=b"data-1",
            previous_hash=b"\x00" * 32,
        )
        chunk2 = QDNDataChunk(
            index=1,
            data=b"data-2",
            previous_hash=chunk1.hash,
        )
        assert chunk2.previous_hash == chunk1.hash
        assert chunk2.hash != chunk1.hash


class TestQTubeManifest:
    def test_to_dict(self, stream_id):
        manifest = QTubeManifest(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            chunk_hashes=["abc123"],
            total_size=1024,
            fragment_count=10,
            duration_ms=10000,
        )
        data = manifest.to_dict()
        assert data["type"] == "qtube-video"
        assert data["streamId"] == stream_id.hex()
        assert data["publisher"] == "test-name"
        assert data["title"] == "Test Stream"
        assert data["chunkHashes"] == ["abc123"]
        assert data["totalSize"] == 1024
        assert data["fragmentCount"] == 10
        assert data["durationMs"] == 10000
        assert data["isPartial"] is False

    def test_to_json(self, stream_id):
        manifest = QTubeManifest(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
        )
        json_str = manifest.to_json()
        assert '"type": "qtube-video"' in json_str
        assert '"publisher": "test-name"' in json_str


class TestArchivalPipeline:
    def test_init(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
        )
        assert pipeline.stream_id == stream_id
        assert pipeline.publisher == "test-name"
        assert pipeline.title == "Test Stream"
        assert pipeline.min_chunk_bytes == QDN_CHUNK_MIN_BYTES
        assert pipeline.max_chunk_bytes == QDN_CHUNK_MAX_BYTES
        assert pipeline.manifest is None
        assert pipeline.qdn_chunks == []
        assert pipeline.stats.state == ArchiveState.IDLE

    def test_add_chunk(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=1024 * 1024,  # 1MB ceiling for testing
        )
        chunk = make_chunk(stream_id, 1)
        pipeline.add_chunk(chunk)
        assert pipeline.stats.fragments_archived == 1
        assert pipeline.stats.bytes_archived == 1024
        assert pipeline.stats.qdn_chunks_created == 0  # Not flushed yet

    def test_chunk_bounds_must_be_positive(self, stream_id):
        with pytest.raises(ArchivalError):
            ArchivalPipeline(
                stream_id=stream_id,
                publisher="test-name",
                title="Test Stream",
                min_chunk_bytes=0,
            )
        with pytest.raises(ArchivalError):
            ArchivalPipeline(
                stream_id=stream_id,
                publisher="test-name",
                title="Test Stream",
                max_chunk_bytes=0,
            )

    def test_min_must_not_exceed_max(self, stream_id):
        with pytest.raises(ArchivalError):
            ArchivalPipeline(
                stream_id=stream_id,
                publisher="test-name",
                title="Test Stream",
                min_chunk_bytes=4096,
                max_chunk_bytes=2048,
            )

    def test_add_chunk_wrong_stream(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
        )
        other_stream = hashlib.sha256(b"other").digest()
        chunk = make_chunk(other_stream, 1)
        with pytest.raises(ArchivalError):
            pipeline.add_chunk(chunk)

    def test_flush_toward_ceiling(self, stream_id):
        # Chunks are sized toward max_chunk_bytes (the ceiling), not the floor.
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,  # 2KB ceiling for testing
        )
        # 3 KB → one full 2 KB chunk flushed mid-stream, 1 KB still buffered.
        for seq in range(1, 4):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        assert pipeline.stats.qdn_chunks_created == 1
        assert pipeline.qdn_chunks[0].size == 2048
        assert pipeline.stats.current_buffer_size == 1024

    def test_multiple_flushes(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,  # 2KB ceiling for testing
        )
        # 8 KB → three full 2 KB chunks flushed mid-stream, 2 KB buffered.
        for seq in range(1, 9):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        assert pipeline.stats.qdn_chunks_created == 3
        assert len(pipeline.qdn_chunks) == 3
        assert all(c.size == 2048 for c in pipeline.qdn_chunks)

    def test_chunks_never_exceed_ceiling(self, stream_id):
        # The flush-before-overflow rule keeps every chunk (mid-stream and the
        # final one) within [min, max].
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 12):  # 11 KB — deliberately not a multiple of 2 KB
            pipeline.add_chunk(make_chunk(stream_id, seq))

        assert pipeline.qdn_chunks  # at least one flushed mid-stream
        assert all(c.size <= 2048 for c in pipeline.qdn_chunks)

        pipeline.finalize()
        assert all(c.size <= 2048 for c in pipeline.qdn_chunks)

    def test_finalize(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 4):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        manifest = pipeline.finalize()
        assert manifest is not None
        assert manifest.publisher == "test-name"
        assert manifest.title == "Test Stream"
        assert manifest.fragment_count == 3
        assert manifest.duration_ms == 3000  # 3 chunks * 1000ms
        assert manifest.total_size == 3072  # 3 chunks * 1024 bytes
        assert len(manifest.chunk_hashes) == 2  # 1 auto-flush + 1 finalize flush
        assert manifest.is_partial is False
        assert pipeline.stats.state == ArchiveState.COMPLETE

    def test_finalize_partial(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 4):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        manifest = pipeline.finalize(is_partial=True)
        assert manifest.is_partial is True

    def test_finalize_empty(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
        )
        with pytest.raises(ArchivalError):
            pipeline.finalize()

    def test_verify_integrity_valid(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 7):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        assert pipeline.verify_integrity() is True

    def test_verify_integrity_tampered(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        # 8 KB → three QDN chunks, so tampering the middle one keeps a successor
        # whose recorded previous_hash no longer matches.
        for seq in range(1, 9):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        # Tamper with a QDN chunk's data
        pipeline.qdn_chunks[1].data = b"\xff" * pipeline.qdn_chunks[1].size
        assert pipeline.verify_integrity() is False

    def test_verify_integrity_tampered_first_chunk(self, stream_id):
        # Tampering the *first* chunk is detected by the chain link to the next
        # chunk (whose recorded previous_hash no longer matches).
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 7):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        pipeline.qdn_chunks[0].data = b"\xff" * pipeline.qdn_chunks[0].size
        assert pipeline.verify_integrity() is False

    def test_flush_on_empty_buffer_is_noop(self, stream_id):
        # _flush() guards an empty buffer. Nothing reaches this guard through
        # add_chunk/finalize, so it is exercised directly.
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        assert pipeline.qdn_chunks == []
        pipeline._flush()
        assert pipeline.qdn_chunks == []
        assert pipeline.stats.qdn_chunks_created == 0

    def test_finalize_after_streaming_flushes(self, stream_id):
        # finalize() emits the buffered remainder after mid-stream flushes.
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 9):  # 8 KB → 3 full 2 KB chunks + 2 KB buffered
            pipeline.add_chunk(make_chunk(stream_id, seq))
        assert pipeline.stats.qdn_chunks_created == 3

        manifest = pipeline.finalize()
        assert manifest.fragment_count == 8
        assert len(manifest.chunk_hashes) == 4  # 3 mid-stream + 1 final
        assert pipeline.verify_integrity() is True

    def test_stats(self, stream_id):
        pipeline = ArchivalPipeline(
            stream_id=stream_id,
            publisher="test-name",
            title="Test Stream",
            min_chunk_bytes=1024,
            max_chunk_bytes=2048,
        )
        for seq in range(1, 4):
            pipeline.add_chunk(make_chunk(stream_id, seq))

        stats = pipeline.stats
        assert stats.fragments_archived == 3
        assert stats.bytes_archived == 3072
        assert stats.qdn_chunks_created == 1
        assert stats.chunks_collected == 1  # 1 chunk still in buffer
        assert stats.current_buffer_size == 1024