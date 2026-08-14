"""QLive QDN signaling integration.

Implements the QDN signaling layer defined in docs/protocol.md section 4.
Handles stream metadata publication, swarm peer lists, encryption keys,
stream discovery, and lifecycle state management.

The signaling layer is the slow, permanent, authoritative layer that
publishes stream information to QDN. It never carries live video data.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StreamStatus(Enum):
    """Stream lifecycle states (from docs/protocol.md section 4.2)."""

    ANNOUNCED = "announced"
    LIVE = "live"
    ENDED = "ended"
    ARCHIVED = "archived"
    INTERRUPTED = "interrupted"


class SignalingError(Exception):
    """Base exception for signaling errors."""


class StreamNotFoundError(SignalingError):
    """Raised when a stream cannot be found."""


@dataclass
class CodecInfo:
    """Codec configuration for a stream."""

    video: str = "h264"
    audio: str = "aac"
    container: str = "cmaf"


@dataclass
class ResolutionInfo:
    """Video resolution for a stream."""

    width: int = 1920
    height: int = 1080
    fps: int = 30


@dataclass
class BitrateInfo:
    """Bitrate configuration for a stream."""

    video: int = 4500000
    audio: int = 128000


@dataclass
class EncryptionInfo:
    """Encryption configuration for a stream."""

    enabled: bool = False
    key_id: str | None = None


@dataclass
class ArchiveInfo:
    """Archive status for a stream."""

    status: str = "pending"
    qdn_resource_id: str | None = None
    qtube_manifest_id: str | None = None


@dataclass
class SwarmInfo:
    """Swarm peer lists for a stream."""

    primary_tree: list[str] = field(default_factory=list)
    mesh_peers: list[str] = field(default_factory=list)


@dataclass
class StreamMetadata:
    """Stream metadata document published to QDN.

    Matches the schema in docs/protocol.md section 4.1.
    """

    publisher: str
    title: str
    description: str = ""
    category: str = "other"
    started_at: int = field(default_factory=lambda: int(time.time() * 1000))
    status: StreamStatus = StreamStatus.ANNOUNCED
    fragment_duration_ms: int = 1000
    codec: CodecInfo = field(default_factory=CodecInfo)
    resolution: ResolutionInfo = field(default_factory=ResolutionInfo)
    bitrate: BitrateInfo = field(default_factory=BitrateInfo)
    renditions: list[int] = field(default_factory=lambda: [1000, 2000, 3000, 4500, 6000])
    encryption: EncryptionInfo = field(default_factory=EncryptionInfo)
    swarm: SwarmInfo = field(default_factory=SwarmInfo)
    archive: ArchiveInfo = field(default_factory=ArchiveInfo)
    version: int = 1

    @property
    def stream_id(self) -> bytes:
        """SHA-256 hash of the stream metadata document."""
        return hashlib.sha256(self.to_json().encode()).digest()

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "type": "qlive-stream",
            "version": self.version,
            "publisher": self.publisher,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "startedAt": self.started_at,
            "status": self.status.value,
            "fragmentDurationMs": self.fragment_duration_ms,
            "codec": {
                "video": self.codec.video,
                "audio": self.codec.audio,
                "container": self.codec.container,
            },
            "resolution": {
                "width": self.resolution.width,
                "height": self.resolution.height,
                "fps": self.resolution.fps,
            },
            "bitrate": {
                "video": self.bitrate.video,
                "audio": self.bitrate.audio,
            },
            "renditions": self.renditions,
            "encryption": {
                "enabled": self.encryption.enabled,
                "keyId": self.encryption.key_id,
            },
            "swarm": {
                "primaryTree": self.swarm.primary_tree,
                "meshPeers": self.swarm.mesh_peers,
            },
            "archive": {
                "status": self.archive.status,
                "qdnResourceId": self.archive.qdn_resource_id,
                "qtubeManifestId": self.archive.qtube_manifest_id,
            },
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamMetadata:
        """Create from a dictionary."""
        try:
            return cls(
                publisher=data["publisher"],
                title=data["title"],
                description=data.get("description", ""),
                category=data.get("category", "other"),
                started_at=data.get("startedAt", int(time.time() * 1000)),
                status=StreamStatus(data.get("status", "announced")),
                fragment_duration_ms=data.get("fragmentDurationMs", 1000),
                codec=CodecInfo(**data.get("codec", {})),
                resolution=ResolutionInfo(**data.get("resolution", {})),
                bitrate=BitrateInfo(**data.get("bitrate", {})),
                renditions=data.get("renditions", [1000, 2000, 3000, 4500, 6000]),
                encryption=EncryptionInfo(
                    enabled=data.get("encryption", {}).get("enabled", False),
                    key_id=data.get("encryption", {}).get("keyId"),
                ),
                swarm=SwarmInfo(
                    primary_tree=data.get("swarm", {}).get("primaryTree", []),
                    mesh_peers=data.get("swarm", {}).get("meshPeers", []),
                ),
                archive=ArchiveInfo(
                    status=data.get("archive", {}).get("status", "pending"),
                    qdn_resource_id=data.get("archive", {}).get("qdnResourceId"),
                    qtube_manifest_id=data.get("archive", {}).get("qtubeManifestId"),
                ),
                version=data.get("version", 1),
            )
        except KeyError as e:
            raise SignalingError(f"Invalid stream metadata: missing {e}") from e

    @classmethod
    def from_json(cls, json_str: str) -> StreamMetadata:
        """Create from a JSON string."""
        return cls.from_dict(json.loads(json_str))


class StreamRegistry:
    """In-memory registry of active streams.

    Simulates the QDN stream discovery layer. In production, this
    would query QDN for stream metadata documents.
    """

    def __init__(self) -> None:
        self._streams: dict[str, StreamMetadata] = {}

    @property
    def streams(self) -> dict[str, StreamMetadata]:
        """All registered streams keyed by stream ID."""
        return self._streams

    def register(self, metadata: StreamMetadata) -> bytes:
        """Register a new stream.

        Returns the stream ID.
        """
        stream_id = metadata.stream_id
        self._streams[stream_id.hex()] = metadata
        return stream_id

    def unregister(self, stream_id: bytes) -> None:
        """Remove a stream from the registry."""
        self._streams.pop(stream_id.hex(), None)

    def get(self, stream_id: bytes) -> StreamMetadata | None:
        """Get a stream by ID."""
        return self._streams.get(stream_id.hex())

    def get_by_publisher(self, publisher: str) -> list[StreamMetadata]:
        """Get all streams by a publisher."""
        return [s for s in self._streams.values() if s.publisher == publisher]

    def get_live(self) -> list[StreamMetadata]:
        """Get all live streams."""
        return [s for s in self._streams.values() if s.status == StreamStatus.LIVE]

    def get_announced(self) -> list[StreamMetadata]:
        """Get all announced (upcoming) streams."""
        return [s for s in self._streams.values() if s.status == StreamStatus.ANNOUNCED]

    def update_status(self, stream_id: bytes, status: StreamStatus) -> None:
        """Update a stream's lifecycle status."""
        stream = self.get(stream_id)
        if not stream:
            raise StreamNotFoundError(f"Stream not found: {stream_id.hex()}")
        stream.status = status

    def update_swarm(
        self,
        stream_id: bytes,
        primary_tree: list[str] | None = None,
        mesh_peers: list[str] | None = None,
    ) -> None:
        """Update a stream's swarm peer lists."""
        stream = self.get(stream_id)
        if not stream:
            raise StreamNotFoundError(f"Stream not found: {stream_id.hex()}")
        if primary_tree is not None:
            stream.swarm.primary_tree = primary_tree
        if mesh_peers is not None:
            stream.swarm.mesh_peers = mesh_peers

    def update_archive(
        self,
        stream_id: bytes,
        status: str,
        qdn_resource_id: str | None = None,
        qtube_manifest_id: str | None = None,
    ) -> None:
        """Update a stream's archive status."""
        stream = self.get(stream_id)
        if not stream:
            raise StreamNotFoundError(f"Stream not found: {stream_id.hex()}")
        stream.archive.status = status
        if qdn_resource_id:
            stream.archive.qdn_resource_id = qdn_resource_id
        if qtube_manifest_id:
            stream.archive.qtube_manifest_id = qtube_manifest_id

    def clear(self) -> None:
        """Clear all streams."""
        self._streams.clear()
