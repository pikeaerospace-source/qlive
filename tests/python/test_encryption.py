"""Tests for the QLive per-stream encryption module."""

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from qlive.encryption import (
    StreamKeyManager,
    decrypt_payload,
    encrypt_payload,
    generate_stream_key,
    unwrap_key,
    wrap_key,
)


def test_roundtrip_encrypt_decrypt():
    key = generate_stream_key()
    payload = b"hello, qlive" * 100
    encrypted = encrypt_payload(payload, key)
    assert encrypted != payload
    assert decrypt_payload(encrypted, key) == payload


def test_encryption_is_nondeterministic():
    key = generate_stream_key()
    payload = b"same payload"
    assert encrypt_payload(payload, key) != encrypt_payload(payload, key)


def test_decrypt_wrong_key_fails():
    payload = b"secret"
    encrypted = encrypt_payload(payload, generate_stream_key())
    with pytest.raises(InvalidTag):
        decrypt_payload(encrypted, generate_stream_key())


def test_key_manager_rotation():
    manager = StreamKeyManager()
    assert manager.key_id == "key-0"
    first_key = manager.key
    new_id = manager.rotate()
    assert new_id == "key-1"
    assert manager.key != first_key


def test_key_envelope_roundtrip():
    viewer_private = X25519PrivateKey.generate()
    stream_key = generate_stream_key()
    envelope = wrap_key(stream_key, viewer_private.public_key())
    assert unwrap_key(envelope, viewer_private) == stream_key


def test_key_envelope_wrong_viewer_fails():
    viewer_private = X25519PrivateKey.generate()
    stream_key = generate_stream_key()
    envelope = wrap_key(stream_key, viewer_private.public_key())

    other_private = X25519PrivateKey.generate()
    with pytest.raises(InvalidTag):
        unwrap_key(envelope, other_private)
