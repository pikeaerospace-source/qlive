"""QLive ephemeral chunk format.

Implements the binary chunk format defined in docs/protocol.md section 3.

Chunk structure:
    Magic:        "QLIV" (4 bytes)
    Version:      uint8 (currently 1)
    Stream ID:    32 bytes (SHA-256 of stream metadata)
    Sequence ID:  uint64 (monotonic per stream)
    Timestamp:    uint64 (milliseconds since epoch)
    Duration:     uint16 (milliseconds)
    Payload Size: uint32 (bytes)
    Payload Hash: 32 bytes (SHA-256 of payload)
    Signature:    64 bytes (Ed25519)
    Payload:      CMAF/fMP4 media data
"""

from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Protocol constants (from docs/protocol.md section 10)
MAGIC = b"QLIV"
VERSION = 1
HEADER_SIZE = 4 + 1 + 32 + 8 + 8 + 2 + 4 + 32 + 64  # 155 bytes
SIGNATURE_BYTES = 64
HASH_BYTES = 32

DEFAULT_FRAGMENT_MS = 1000
MIN_FRAGMENT_MS = 500
MAX_FRAGMENT_MS = 2000


class ChunkError(Exception):
    """Base exception for chunk errors."""


class ChunkFormatError(ChunkError):
    """Raised when a chunk fails format validation."""


class ChunkSignatureError(ChunkError):
    """Raised when a chunk signature verification fails."""


@dataclass
class Chunk:
    """A single signed ephemeral media chunk."""

    stream_id: bytes
    sequence_id: int
    timestamp: int
    duration: int
    payload: bytes
    signature: bytes = b""
    version: int = VERSION

    @property
    def payload_hash(self) -> bytes:
        """SHA-256 hash of the payload."""
        return hashlib.sha256(self.payload).digest()

    @property
    def header(self) -> bytes:
        """Serialize the chunk header (all fields except signature and payload)."""
        return struct.pack(
            "!4sB32sQQH I32s".replace(" ", ""),
            MAGIC,
            self.version,
            self.stream_id,
            self.sequence_id,
            self.timestamp,
            self.duration,
            len(self.payload),
            self.payload_hash,
        )

    @property
    def signing_data(self) -> bytes:
        """Data covered by the signature: the header.

        The serialized header already embeds the SHA-256 ``payload_hash``, so
        signing the 91-byte header — not the full payload — keeps the Ed25519
        sign/verify cost constant regardless of bitrate while still binding the
        signature to the payload (tampering changes the header's ``payload_hash``)
        — see docs/ENCRYPTION-MODEL.md.
        """
        return self.header

    def sign(self, private_key: ed25519.Ed25519PrivateKey) -> Chunk:
        """Sign this chunk with the broadcaster's Ed25519 private key."""
        self.signature = private_key.sign(self.signing_data)
        return self

    def verify(self, public_key: ed25519.Ed25519PublicKey) -> bool:
        """Verify the chunk signature against the broadcaster's public key."""
        if not self.signature:
            raise ChunkSignatureError("Chunk is not signed")
        try:
            public_key.verify(self.signature, self.signing_data)
            return True
        except InvalidSignature:
            return False

    def serialize(self) -> bytes:
        """Serialize the complete chunk (header + signature + payload)."""
        if not self.signature:
            raise ChunkError("Cannot serialize unsigned chunk")
        return self.header + self.signature + self.payload

    @classmethod
    def deserialize(cls, data: bytes) -> Chunk:
        """Deserialize a chunk from bytes."""
        if len(data) < HEADER_SIZE:
            raise ChunkFormatError(f"Chunk too short: {len(data)} bytes, minimum {HEADER_SIZE}")

        # Parse header fields
        magic = data[0:4]
        if magic != MAGIC:
            raise ChunkFormatError(f"Invalid magic: {magic!r}")

        version = data[4]
        if version != VERSION:
            raise ChunkFormatError(f"Unsupported version: {version}")

        stream_id = data[5:37]
        sequence_id = struct.unpack("!Q", data[37:45])[0]
        timestamp = struct.unpack("!Q", data[45:53])[0]
        duration = struct.unpack("!H", data[53:55])[0]
        payload_size = struct.unpack("!I", data[55:59])[0]
        payload_hash = data[59:91]
        signature = data[91:155]

        # Validate payload size
        if len(data) != HEADER_SIZE + payload_size:
            raise ChunkFormatError(
                f"Payload size mismatch: header says {payload_size}, "
                f"actual {len(data) - HEADER_SIZE}"
            )

        payload = data[HEADER_SIZE:]

        # Validate payload hash
        actual_hash = hashlib.sha256(payload).digest()
        if actual_hash != payload_hash:
            raise ChunkFormatError("Payload hash mismatch")

        # Validate duration
        if not (MIN_FRAGMENT_MS <= duration <= MAX_FRAGMENT_MS):
            raise ChunkFormatError(f"Invalid duration: {duration}ms")

        return cls(
            stream_id=stream_id,
            sequence_id=sequence_id,
            timestamp=timestamp,
            duration=duration,
            payload=payload,
            signature=signature,
            version=version,
        )

    def __repr__(self) -> str:
        return (
            f"Chunk(stream_id={self.stream_id.hex()[:8]}..., "
            f"seq={self.sequence_id}, ts={self.timestamp}, "
            f"duration={self.duration}ms, payload={len(self.payload)}B, "
            f"signed={bool(self.signature)})"
        )


def create_chunk(
    stream_id: bytes,
    sequence_id: int,
    payload: bytes,
    duration: int = DEFAULT_FRAGMENT_MS,
    timestamp: int | None = None,
) -> Chunk:
    """Create a new unsigned chunk."""
    if len(stream_id) != HASH_BYTES:
        raise ChunkFormatError(f"Stream ID must be {HASH_BYTES} bytes")
    if not (MIN_FRAGMENT_MS <= duration <= MAX_FRAGMENT_MS):
        raise ChunkFormatError(f"Duration must be {MIN_FRAGMENT_MS}-{MAX_FRAGMENT_MS}ms")
    if sequence_id < 1:
        raise ChunkFormatError("Sequence ID must be >= 1")

    return Chunk(
        stream_id=stream_id,
        sequence_id=sequence_id,
        timestamp=timestamp if timestamp is not None else int(time.time() * 1000),
        duration=duration,
        payload=payload,
    )


def load_private_key(pem_data: bytes) -> ed25519.Ed25519PrivateKey:
    """Load an Ed25519 private key from PEM data."""
    key = serialization.load_pem_private_key(pem_data, password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise TypeError("Key is not an Ed25519 private key")
    return key


def load_public_key(pem_data: bytes) -> ed25519.Ed25519PublicKey:
    """Load an Ed25519 public key from PEM data."""
    key = serialization.load_pem_public_key(pem_data)
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise TypeError("Key is not an Ed25519 public key")
    return key
