"""QLive proof-of-relay bandwidth receipts.

Implements the proof-of-relay incentive model defined in
docs/protocol.md section 9.2 and docs/monetization.md section 3.

Relay nodes collect signed bandwidth receipts from downstream peers
as proof that they served video data. These receipts can be redeemed
against a stream's bounty pool for QORT rewards.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


class ProofError(Exception):
    """Base exception for proof-of-relay errors."""


class ReceiptState(Enum):
    """Receipt lifecycle states."""

    PENDING = "pending"
    VERIFIED = "verified"
    REDEEMED = "redeemed"
    REJECTED = "rejected"


@dataclass
class BandwidthReceipt:
    """A signed bandwidth receipt from a downstream peer.

    Proves that a relay node served video data to a downstream peer.
    """

    relay_node_id: str
    downstream_node_id: str
    stream_id: bytes
    bytes_relayed: int
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    signature: bytes = b""
    state: ReceiptState = ReceiptState.PENDING

    @property
    def signing_data(self) -> bytes:
        """Data covered by the signature."""
        return (
            self.relay_node_id.encode()
            + b"|"
            + self.downstream_node_id.encode()
            + b"|"
            + self.stream_id
            + b"|"
            + self.bytes_relayed.to_bytes(8, "big")
            + b"|"
            + self.timestamp.to_bytes(8, "big")
        )

    def sign(self, private_key: ed25519.Ed25519PrivateKey) -> "BandwidthReceipt":
        """Sign the receipt with the downstream node's private key."""
        self.signature = private_key.sign(self.signing_data)
        return self

    def verify(self, public_key: ed25519.Ed25519PublicKey) -> bool:
        """Verify the receipt signature against the downstream node's key."""
        if not self.signature:
            raise ProofError("Receipt is not signed")
        try:
            public_key.verify(self.signature, self.signing_data)
            return True
        except InvalidSignature:
            return False


@dataclass
class ProofStats:
    """Statistics for proof-of-relay monitoring."""

    total_receipts: int = 0
    verified: int = 0
    redeemed: int = 0
    rejected: int = 0
    total_bytes_proven: int = 0
    total_qort_earned: float = 0.0


class ProofOfRelayManager:
    """Manages bandwidth receipts for proof-of-relay.

    Handles receipt creation, verification, redemption, and statistics.
    """

    def __init__(
        self,
        qort_per_mb: float = 0.001,
        redemption_delay_seconds: int = 86400,  # 24h dispute window
    ) -> None:
        self.qort_per_mb = qort_per_mb
        self.redemption_delay_seconds = redemption_delay_seconds
        self._receipts: list[BandwidthReceipt] = []
        self._stats = ProofStats()

    @property
    def stats(self) -> ProofStats:
        """Current proof-of-relay statistics."""
        self._update_stats()
        return self._stats

    @property
    def receipts(self) -> list[BandwidthReceipt]:
        """All receipts collected."""
        return self._receipts

    def create_receipt(
        self,
        relay_node_id: str,
        downstream_node_id: str,
        stream_id: bytes,
        bytes_relayed: int,
    ) -> BandwidthReceipt:
        """Create a new unsigned bandwidth receipt."""
        receipt = BandwidthReceipt(
            relay_node_id=relay_node_id,
            downstream_node_id=downstream_node_id,
            stream_id=stream_id,
            bytes_relayed=bytes_relayed,
        )
        self._receipts.append(receipt)
        return receipt

    def verify_receipt(
        self,
        receipt: BandwidthReceipt,
        public_key: ed25519.Ed25519PublicKey,
    ) -> bool:
        """Verify a receipt's signature.

        Returns True if the receipt is valid.
        """
        if receipt.state == ReceiptState.REDEEMED:
            return False

        if receipt.verify(public_key):
            receipt.state = ReceiptState.VERIFIED
            return True

        receipt.state = ReceiptState.REJECTED
        return False

    def can_redeem(self, receipt: BandwidthReceipt) -> bool:
        """Whether a receipt is eligible for redemption.

        Receipts must be verified and past the dispute window.
        """
        if receipt.state != ReceiptState.VERIFIED:
            return False
        age = int(time.time() * 1000) - receipt.timestamp
        return age >= self.redemption_delay_seconds * 1000

    def redeem(self, receipt: BandwidthReceipt) -> float:
        """Redeem a verified receipt for QORT.

        Returns the QORT amount earned.
        """
        if not self.can_redeem(receipt):
            raise ProofError("Receipt is not eligible for redemption")

        qort_earned = self._calculate_qort(receipt.bytes_relayed)
        receipt.state = ReceiptState.REDEEMED
        self._stats.total_qort_earned += qort_earned
        return qort_earned

    def get_earnings(self, relay_node_id: str) -> float:
        """Get total QORT earned by a relay node."""
        return sum(
            self._calculate_qort(r.bytes_relayed)
            for r in self._receipts
            if r.relay_node_id == relay_node_id
            and r.state == ReceiptState.REDEEMED
        )

    def get_pending_earnings(self, relay_node_id: str) -> float:
        """Get QORT pending redemption for a relay node."""
        return sum(
            self._calculate_qort(r.bytes_relayed)
            for r in self._receipts
            if r.relay_node_id == relay_node_id
            and r.state == ReceiptState.VERIFIED
        )

    def _calculate_qort(self, bytes_relayed: int) -> float:
        """Calculate QORT earned for a given byte count."""
        mb = bytes_relayed / (1024 * 1024)
        return mb * self.qort_per_mb

    def _update_stats(self) -> None:
        """Refresh proof-of-relay statistics."""
        self._stats.total_receipts = len(self._receipts)
        self._stats.verified = sum(
            1 for r in self._receipts if r.state == ReceiptState.VERIFIED
        )
        self._stats.redeemed = sum(
            1 for r in self._receipts if r.state == ReceiptState.REDEEMED
        )
        self._stats.rejected = sum(
            1 for r in self._receipts if r.state == ReceiptState.REJECTED
        )
        self._stats.total_bytes_proven = sum(
            r.bytes_relayed for r in self._receipts
            if r.state in (ReceiptState.VERIFIED, ReceiptState.REDEEMED)
        )