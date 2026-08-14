"""QLive Live → VOD archival pipeline.

Implements the archival pipeline defined in docs/protocol.md section 7.
Aggregates expired live chunks into standard QDN data chunks (10MB-50MB),
generates Q-Tube manifests, and manages the automatic publish on stream end.

The pipeline runs as a background process on the broadcaster's node,
collecting chunks as they fall out of the live sliding window.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from qlive.chunk import Chunk

# Archival constants (from docs/protocol.md section 10)
QDN_CHUNK_MIN_BYTES = 10 * 1024 * 1024  # 10 MB
QDN_CHUNK_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class ArchiveState(Enum):
    """Archive pipeline states."""

    IDLE = "idle"
    COLLECTING = "collecting"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"


class ArchivalError(Exception):
    """Base exception for archival errors."""


@dataclass
class QDNDataChunk:
    """A single QDN data chunk containing aggregated live fragments.

    Chunks are linked in a hash chain for integrity verification.
    """

    index: int
    data: bytes
    previous_hash: bytes
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def hash(self) -> bytes:
        """SHA-256 hash of this chunk (data + previous hash + index)."""
        return hashlib.sha256(
            self.index.to_bytes(8, "big")
            + self.previous_hash
            + self.data
        ).digest()

    @property
    def size(self) -> int:
        """Size of the chunk data in bytes."""
        return len(self.data)


@dataclass
class QTubeManifest:
    """Q-Tube manifest for a completed live stream archive."""

    stream_id: bytes
    publisher: str
    title: str
    description: str = ""
    category: str = "other"
    started_at: int = 0
    ended_at: int = 0
    chunk_hashes: list[str] = field(default_factory=list)
    total_size: int = 0
    fragment_count: int = 0
    duration_ms: int = 0
    codec: str = "h264"
    resolution: str = "1920x1080"
    fps: int = 30
    is_partial: bool = False

    def to_dict(self) -> dict:
        """Convert to a dictionary for JSON serialization."""
        return {
            "type": "qtube-video",
            "version": 1,
            "streamId": self.stream_id.hex(),
            "publisher": self.publisher,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
            "chunkHashes": self.chunk_hashes,
            "totalSize": self.total_size,
            "fragmentCount": self.fragment_count,
            "durationMs": self.duration_ms,
            "codec": self.codec,
            "resolution": self.resolution,
            "fps": self.fps,
            "isPartial": self.is_partial,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ArchiveStats:
    """Statistics for archive monitoring."""

    state: ArchiveState = ArchiveState.IDLE
    chunks_collected: int = 0
    fragments_archived: int = 0
    bytes_archived: int = 0
    qdn_chunks_created: int = 0
    current_buffer_size: int = 0
    is_partial: bool = False


class ArchivalPipeline:
    """Background archival pipeline for live → VOD conversion.

    Collects chunks as they expire from the live window, aggregates
    them into QDN data chunks, and generates a Q-Tube manifest when
    the stream ends.
    """

    def __init__(
        self,
        stream_id: bytes,
        publisher: str,
        title: str,
        description: str = "",
        category: str = "other",
        min_chunk_bytes: int = QDN_CHUNK_MIN_BYTES,
        max_chunk_bytes: int = QDN_CHUNK_MAX_BYTES,
    ) -> None:
        self.stream_id = stream_id
        self.publisher = publisher
        self.title = title
        self.description = description
        self.category = category
        self.min_chunk_bytes = min_chunk_bytes
        self.max_chunk_bytes = max_chunk_bytes
        self.started_at = int(time.time() * 1000)
        self._buffer: list[Chunk] = []
        self._buffer_size = 0
        self._qdn_chunks: list[QDNDataChunk] = []
        self._previous_hash = b"\x00" * 32
        self._total_duration = 0
        self._stats = ArchiveStats()
        self._manifest: Optional[QTubeManifest] = None

    @property
    def stats(self) -> ArchiveStats:
        """Current archive statistics."""
        self._update_stats()
        return self._stats

    @property
    def manifest(self) -> Optional[QTubeManifest]:
        """The generated Q-Tube manifest (None until stream ends)."""
        return self._manifest

    @property
    def qdn_chunks(self) -> list[QDNDataChunk]:
        """The QDN data chunks created so far."""
        return self._qdn_chunks

    def add_chunk(self, chunk: Chunk) -> None:
        """Add an expired live chunk to the archive buffer.

        Chunks are buffered until they reach the minimum QDN chunk
        size, then flushed as a QDN data chunk.
        """
        if chunk.stream_id != self.stream_id:
            raise ArchivalError("Chunk stream ID does not match archive stream")

        self._buffer.append(chunk)
        self._buffer_size += len(chunk.payload)
        self._total_duration += chunk.duration
        self._stats.fragments_archived += 1
        self._stats.bytes_archived += len(chunk.payload)

        # Flush when buffer reaches minimum chunk size
        if self._buffer_size >= self.min_chunk_bytes:
            self._flush()

    def finalize(self, is_partial: bool = False) -> QTubeManifest:
        """Finalize the archive and generate a Q-Tube manifest.

        Flushes any remaining buffered chunks and creates the manifest.

        Args:
            is_partial: Whether the archive is partial (stream interrupted).

        Returns:
            The generated Q-Tube manifest.
        """
        # Flush any remaining buffered chunks
        if self._buffer:
            self._flush()

        if not self._qdn_chunks:
            raise ArchivalError("Cannot finalize empty archive")

        self._stats.is_partial = is_partial
        self._stats.state = ArchiveState.COMPLETE

        self._manifest = QTubeManifest(
            stream_id=self.stream_id,
            publisher=self.publisher,
            title=self.title,
            description=self.description,
            category=self.category,
            started_at=self.started_at,
            ended_at=int(time.time() * 1000),
            chunk_hashes=[c.hash.hex() for c in self._qdn_chunks],
            total_size=sum(c.size for c in self._qdn_chunks),
            fragment_count=self._stats.fragments_archived,
            duration_ms=self._total_duration,
            is_partial=is_partial,
        )
        return self._manifest

    def verify_integrity(self) -> bool:
        """Verify the hash chain integrity of all QDN chunks.

        Returns True if the hash chain is valid.
        """
        previous = b"\x00" * 32
        for chunk in self._qdn_chunks:
            if chunk.previous_hash != previous:
                return False
            expected = hashlib.sha256(
                chunk.index.to_bytes(8, "big") + previous + chunk.data
            ).digest()
            if chunk.hash != expected:
                return False
            previous = chunk.hash
        return True

    def _flush(self) -> None:
        """Flush the buffer as a QDN data chunk."""
        if not self._buffer:
            return

        # Concatenate chunk payloads
        data = b"".join(c.payload for c in self._buffer)

        # Create QDN data chunk
        qdn_chunk = QDNDataChunk(
            index=len(self._qdn_chunks),
            data=data,
            previous_hash=self._previous_hash,
        )
        self._qdn_chunks.append(qdn_chunk)
        self._previous_hash = qdn_chunk.hash

        # Reset buffer
        self._buffer = []
        self._buffer_size = 0
        self._stats.qdn_chunks_created += 1

    def _update_stats(self) -> None:
        """Refresh archive statistics."""
        self._stats.chunks_collected = len(self._buffer)
        self._stats.current_buffer_size = self._buffer_size
        self._stats.qdn_chunks_created = len(self._qdn_chunks)