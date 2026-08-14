"""Tests for the QLive proof-of-relay bandwidth receipts."""

import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.proof import (
    BandwidthReceipt,
    ProofError,
    ProofOfRelayManager,
    ProofStats,
    ReceiptState,
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


class TestBandwidthReceipt:
    def test_init(self, stream_id):
        receipt = BandwidthReceipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        assert receipt.relay_node_id == "relay-1"
        assert receipt.downstream_node_id == "viewer-1"
        assert receipt.stream_id == stream_id
        assert receipt.bytes_relayed == 1024
        assert receipt.signature == b""
        assert receipt.state == ReceiptState.PENDING

    def test_signing_data(self, stream_id):
        receipt = BandwidthReceipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
            start_sequence=1,
            end_sequence=10,
            timestamp=1234567890,
        )
        expected = (
            b"relay-1|viewer-1|"
            + stream_id
            + b"|"
            + (1024).to_bytes(8, "big")
            + b"|"
            + (1).to_bytes(8, "big")
            + b"|"
            + (10).to_bytes(8, "big")
            + b"|"
            + (1234567890).to_bytes(8, "big")
        )
        assert receipt.signing_data == expected

    def test_overlaps(self, stream_id):
        a = BandwidthReceipt("relay-1", "viewer-1", stream_id, 1024, start_sequence=1, end_sequence=10)
        b = BandwidthReceipt("relay-1", "viewer-1", stream_id, 1024, start_sequence=5, end_sequence=15)
        c = BandwidthReceipt("relay-1", "viewer-1", stream_id, 1024, start_sequence=11, end_sequence=20)
        no_range = BandwidthReceipt("relay-1", "viewer-1", stream_id, 1024)
        assert a.overlaps(b) is True
        assert a.overlaps(c) is False
        assert a.overlaps(no_range) is False
        assert no_range.has_range is False

    def test_sign_and_verify(self, stream_id, key_pair):
        private_key, public_key = key_pair
        receipt = BandwidthReceipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)
        assert receipt.signature
        assert receipt.verify(public_key) is True

    def test_verify_wrong_key(self, stream_id, key_pair):
        private_key, _ = key_pair
        other_private = ed25519.Ed25519PrivateKey.generate()
        other_public = other_private.public_key()

        receipt = BandwidthReceipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)
        assert receipt.verify(other_public) is False

    def test_verify_unsigned(self, stream_id, key_pair):
        _, public_key = key_pair
        receipt = BandwidthReceipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        with pytest.raises(ProofError):
            receipt.verify(public_key)


class TestProofStats:
    def test_init(self):
        stats = ProofStats()
        assert stats.total_receipts == 0
        assert stats.verified == 0
        assert stats.redeemed == 0
        assert stats.rejected == 0
        assert stats.total_bytes_proven == 0
        assert stats.total_qort_earned == 0.0


class TestProofOfRelayManager:
    def test_init(self):
        manager = ProofOfRelayManager()
        assert manager.qort_per_mb == 0.001
        assert manager.redemption_delay_seconds == 86400
        assert manager.receipts == []
        assert manager.stats.total_receipts == 0

    def test_create_receipt(self, stream_id):
        manager = ProofOfRelayManager()
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        assert receipt.relay_node_id == "relay-1"
        assert receipt.state == ReceiptState.PENDING
        assert len(manager.receipts) == 1

    def test_verify_receipt_valid(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager()
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)

        assert manager.verify_receipt(receipt, public_key) is True
        assert receipt.state == ReceiptState.VERIFIED
        assert manager.stats.verified == 1

    def test_verify_receipt_invalid(self, stream_id, key_pair):
        private_key, _ = key_pair
        other_private = ed25519.Ed25519PrivateKey.generate()
        other_public = other_private.public_key()

        manager = ProofOfRelayManager()
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)

        assert manager.verify_receipt(receipt, other_public) is False
        assert receipt.state == ReceiptState.REJECTED
        assert manager.stats.rejected == 1

    def test_double_counting_rejected(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager()

        first = manager.create_receipt(
            "relay-1", "viewer-1", stream_id, 1024, start_sequence=1, end_sequence=10
        )
        first.sign(private_key)
        assert manager.verify_receipt(first, public_key) is True

        # Overlapping receipt should be rejected as double-counted.
        second = manager.create_receipt(
            "relay-1", "viewer-1", stream_id, 1024, start_sequence=5, end_sequence=15
        )
        second.sign(private_key)
        assert manager.verify_receipt(second, public_key) is False
        assert second.state == ReceiptState.REJECTED

        # Non-overlapping receipt should pass.
        third = manager.create_receipt(
            "relay-1", "viewer-1", stream_id, 1024, start_sequence=11, end_sequence=20
        )
        third.sign(private_key)
        assert manager.verify_receipt(third, public_key) is True

    def test_verify_redeemed_receipt(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=0)
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)
        manager.verify_receipt(receipt, public_key)
        manager.redeem(receipt)

        # Can't verify a redeemed receipt
        assert manager.verify_receipt(receipt, public_key) is False

    def test_can_redeem_verified(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=0)
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)
        manager.verify_receipt(receipt, public_key)
        assert manager.can_redeem(receipt) is True

    def test_can_redeem_pending(self, stream_id):
        manager = ProofOfRelayManager()
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        assert manager.can_redeem(receipt) is False

    def test_can_redeem_dispute_window(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=3600)
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        receipt.sign(private_key)
        manager.verify_receipt(receipt, public_key)
        assert manager.can_redeem(receipt) is False  # Within dispute window

    def test_redeem(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=0)
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024 * 1024,  # 1 MB
        )
        receipt.sign(private_key)
        manager.verify_receipt(receipt, public_key)

        qort = manager.redeem(receipt)
        assert qort == 0.001  # 1 MB * 0.001 QORT/MB
        assert receipt.state == ReceiptState.REDEEMED
        assert manager.stats.redeemed == 1
        assert manager.stats.total_qort_earned == 0.001

    def test_redeem_not_eligible(self, stream_id):
        manager = ProofOfRelayManager()
        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024,
        )
        with pytest.raises(ProofError):
            manager.redeem(receipt)

    def test_get_earnings(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=0)

        # Two receipts for relay-1
        for _ in range(2):
            receipt = manager.create_receipt(
                relay_node_id="relay-1",
                downstream_node_id="viewer-1",
                stream_id=stream_id,
                bytes_relayed=1024 * 1024,  # 1 MB each
            )
            receipt.sign(private_key)
            manager.verify_receipt(receipt, public_key)
            manager.redeem(receipt)

        # One receipt for relay-2
        receipt2 = manager.create_receipt(
            relay_node_id="relay-2",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024 * 1024,
        )
        receipt2.sign(private_key)
        manager.verify_receipt(receipt2, public_key)
        manager.redeem(receipt2)

        assert manager.get_earnings("relay-1") == 0.002
        assert manager.get_earnings("relay-2") == 0.001

    def test_get_pending_earnings(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=3600)

        receipt = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024 * 1024,  # 1 MB
        )
        receipt.sign(private_key)
        manager.verify_receipt(receipt, public_key)

        assert manager.get_pending_earnings("relay-1") == 0.001
        assert manager.get_earnings("relay-1") == 0.0  # Not redeemed yet

    def test_stats(self, stream_id, key_pair):
        private_key, public_key = key_pair
        manager = ProofOfRelayManager(redemption_delay_seconds=0)

        # Valid receipt
        valid = manager.create_receipt(
            relay_node_id="relay-1",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024 * 1024,
        )
        valid.sign(private_key)
        manager.verify_receipt(valid, public_key)
        manager.redeem(valid)

        # Invalid receipt
        invalid = manager.create_receipt(
            relay_node_id="relay-2",
            downstream_node_id="viewer-1",
            stream_id=stream_id,
            bytes_relayed=1024 * 1024,
        )
        invalid.sign(private_key)
        other_public = ed25519.Ed25519PrivateKey.generate().public_key()
        manager.verify_receipt(invalid, other_public)

        stats = manager.stats
        assert stats.total_receipts == 2
        assert stats.verified == 0  # Redeemed receipts no longer verified
        assert stats.redeemed == 1
        assert stats.rejected == 1
        assert stats.total_bytes_proven == 1024 * 1024
        assert stats.total_qort_earned == 0.001