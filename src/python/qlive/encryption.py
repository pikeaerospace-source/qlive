"""Per-stream encryption for QLive private streams.

Implements the encryption model from docs/ENCRYPTION-MODEL.md:

- A per-stream symmetric key (AES-256-GCM) encrypts chunk payloads; the chunk
  header stays plaintext for routing and signature verification.
- The key rotates periodically; each rotation gets a new ``key_id``.
- The stream key is distributed to authorized viewers via hybrid key envelopes
  (ephemeral X25519 + HKDF + AES-256-GCM), so the data plane stays
  multicast-efficient while authorization is per-viewer.

All of this is offline and uses only the ``cryptography`` package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

NONCE_BYTES = 12
X25519_KEY_BYTES = 32
_ENVELOPE_INFO = b"qlive-key-envelope-v1"


def generate_stream_key() -> bytes:
    """Generate a fresh AES-256-GCM key for a stream."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_payload(payload: bytes, key: bytes) -> bytes:
    """Encrypt a chunk payload.

    Returns ``nonce + ciphertext`` (the AES-GCM auth tag is appended to the
    ciphertext by the AEAD). The nonce is prepended so decryption is
    self-contained.
    """
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, payload, None)


def decrypt_payload(data: bytes, key: bytes) -> bytes:
    """Decrypt a payload produced by :func:`encrypt_payload`."""
    nonce = data[:NONCE_BYTES]
    ciphertext = data[NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, ciphertext, None)


@dataclass
class StreamKeyManager:
    """Manages a rotating per-stream symmetric key."""

    key_id: str = "key-0"
    _key: bytes = field(default_factory=generate_stream_key)
    _counter: int = field(default=0, init=False)

    @property
    def key(self) -> bytes:
        """The current stream key."""
        return self._key

    def rotate(self) -> str:
        """Rotate to a fresh key, returning the new ``key_id``."""
        self._key = generate_stream_key()
        self._counter += 1
        self.key_id = f"key-{self._counter}"
        return self.key_id


def wrap_key(stream_key: bytes, viewer_public: X25519PublicKey) -> bytes:
    """Wrap a stream key for a single viewer (hybrid envelope).

    Uses an ephemeral X25519 key exchange + HKDF to derive a wrapping key,
    then AES-256-GCM to encrypt the stream key. Returns
    ``ephemeral_public + nonce + ciphertext``.
    """
    ephemeral = X25519PrivateKey.generate()
    shared = ephemeral.exchange(viewer_public)
    wrapping_key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_ENVELOPE_INFO
    ).derive(shared)
    nonce = os.urandom(NONCE_BYTES)
    wrapped = AESGCM(wrapping_key).encrypt(nonce, stream_key, None)
    ephemeral_public = ephemeral.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return ephemeral_public + nonce + wrapped


def unwrap_key(data: bytes, viewer_private: X25519PrivateKey) -> bytes:
    """Unwrap a stream key produced by :func:`wrap_key`."""
    ephemeral_public = X25519PublicKey.from_public_bytes(data[:X25519_KEY_BYTES])
    nonce = data[X25519_KEY_BYTES : X25519_KEY_BYTES + NONCE_BYTES]
    wrapped = data[X25519_KEY_BYTES + NONCE_BYTES :]
    shared = viewer_private.exchange(ephemeral_public)
    wrapping_key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_ENVELOPE_INFO
    ).derive(shared)
    return AESGCM(wrapping_key).decrypt(nonce, wrapped, None)
