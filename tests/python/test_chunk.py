"""Tests for the QLive ephemeral chunk format."""

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.chunk import (
    DEFAULT_FRAGMENT_MS,
    HASH_BYTES,
    HEADER_SIZE,
    MAGIC,
    MAX_FRAGMENT_MS,
    MIN_FRAGMENT_MS,
    VERSION,
    Chunk,
    ChunkError,
    ChunkFormatError,
    ChunkSignatureError,
    create_chunk,
)


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"test-stream").digest()


@pytest.fixture
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """A fresh Ed25519 key pair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


@pytest.fixture
def sample_payload() -> bytes:
    """Sample media payload (simulated CMAF fragment)."""
    return b"\x00" * 1024  # 1KB of fake media data


class TestCreateChunk:
    def test_create_valid_chunk(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, sequence_id=1, payload=sample_payload)
        assert chunk.stream_id == stream_id
        assert chunk.sequence_id == 1
        assert chunk.duration == DEFAULT_FRAGMENT_MS
        assert chunk.payload == sample_payload
        assert chunk.version == VERSION
        assert chunk.signature == b""

    def test_create_with_custom_duration(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload, duration=500)
        assert chunk.duration == 500

    def test_create_with_timestamp(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload, timestamp=1234567890)
        assert chunk.timestamp == 1234567890

    def test_invalid_stream_id_length(self, sample_payload):
        with pytest.raises(ChunkFormatError):
            create_chunk(b"short", 1, sample_payload)

    def test_invalid_duration_too_short(self, stream_id, sample_payload):
        with pytest.raises(ChunkFormatError):
            create_chunk(stream_id, 1, sample_payload, duration=MIN_FRAGMENT_MS - 1)

    def test_invalid_duration_too_long(self, stream_id, sample_payload):
        with pytest.raises(ChunkFormatError):
            create_chunk(stream_id, 1, sample_payload, duration=MAX_FRAGMENT_MS + 1)

    def test_invalid_sequence_id(self, stream_id, sample_payload):
        with pytest.raises(ChunkFormatError):
            create_chunk(stream_id, 0, sample_payload)


class TestChunkProperties:
    def test_payload_hash(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        assert chunk.payload_hash == hashlib.sha256(sample_payload).digest()

    def test_header_size(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        assert len(chunk.header) == HEADER_SIZE - 64  # header excludes signature

    def test_header_magic(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        assert chunk.header[0:4] == MAGIC

    def test_signing_data_includes_payload(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        assert chunk.signing_data == chunk.header + chunk.payload


class TestSigning:
    def test_sign_and_verify(self, stream_id, sample_payload, key_pair):
        private_key, public_key = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        assert chunk.signature
        assert len(chunk.signature) == 64
        assert chunk.verify(public_key) is True

    def test_verify_wrong_key(self, stream_id, sample_payload, key_pair):
        private_key, _ = key_pair
        other_private = ed25519.Ed25519PrivateKey.generate()
        other_public = other_private.public_key()

        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        assert chunk.verify(other_public) is False

    def test_verify_unsigned_chunk(self, stream_id, sample_payload, key_pair):
        _, public_key = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        with pytest.raises(ChunkSignatureError):
            chunk.verify(public_key)

    def test_tampered_payload_fails_verification(
        self, stream_id, sample_payload, key_pair
    ):
        private_key, public_key = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)

        # Tamper with the payload
        chunk.payload = b"\xff" * len(sample_payload)
        assert chunk.verify(public_key) is False


class TestSerialization:
    def test_roundtrip(self, stream_id, sample_payload, key_pair):
        private_key, public_key = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)

        data = chunk.serialize()
        assert len(data) == HEADER_SIZE + len(sample_payload)

        deserialized = Chunk.deserialize(data)
        assert deserialized.stream_id == stream_id
        assert deserialized.sequence_id == 1
        assert deserialized.timestamp == chunk.timestamp
        assert deserialized.duration == chunk.duration
        assert deserialized.payload == sample_payload
        assert deserialized.signature == chunk.signature
        assert deserialized.verify(public_key) is True

    def test_serialize_unsigned_chunk(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        with pytest.raises(ChunkError):
            chunk.serialize()

    def test_deserialize_too_short(self):
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(b"\x00" * 10)

    def test_deserialize_invalid_magic(self, stream_id, sample_payload, key_pair):
        private_key, _ = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        data = bytearray(chunk.serialize())
        data[0:4] = b"XXXX"
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(bytes(data))

    def test_deserialize_invalid_version(self, stream_id, sample_payload, key_pair):
        private_key, _ = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        data = bytearray(chunk.serialize())
        data[4] = 99
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(bytes(data))

    def test_deserialize_payload_size_mismatch(
        self, stream_id, sample_payload, key_pair
    ):
        private_key, _ = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        data = chunk.serialize()
        # Truncate the payload
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(data[:-10])

    def test_deserialize_payload_hash_mismatch(
        self, stream_id, sample_payload, key_pair
    ):
        private_key, _ = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        data = bytearray(chunk.serialize())
        # Corrupt a payload byte (after the header)
        data[HEADER_SIZE] ^= 0xFF
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(bytes(data))

    def test_deserialize_invalid_duration(self, stream_id, sample_payload, key_pair):
        private_key, _ = key_pair
        chunk = create_chunk(stream_id, 1, sample_payload)
        chunk.sign(private_key)
        data = bytearray(chunk.serialize())
        # Corrupt duration field (bytes 53-55)
        data[53:55] = (9999).to_bytes(2, "big")
        with pytest.raises(ChunkFormatError):
            Chunk.deserialize(bytes(data))


class TestChunkRepr:
    def test_repr(self, stream_id, sample_payload):
        chunk = create_chunk(stream_id, 1, sample_payload)
        assert "Chunk(" in repr(chunk)
        assert f"seq={chunk.sequence_id}" in repr(chunk)
        assert f"duration={chunk.duration}ms" in repr(chunk)
        assert f"payload={len(chunk.payload)}B" in repr(chunk)
        assert "signed=False" in repr(chunk)