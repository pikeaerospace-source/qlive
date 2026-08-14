"""QLive tit-for-tat data swapping and bandwidth tracking.

Implements the incentive model defined in docs/protocol.md section 9.
Tracks bandwidth contributions between peers, prioritizes contributing
peers, and detects free-riders.

The tit-for-tat model ensures peers actually relay video traffic rather
than just leeching bandwidth. Nodes that contribute bandwidth get
priority; free-riders are deprioritized and eventually disconnected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class PeerContribution(Enum):
    """Peer contribution levels based on bandwidth ratio."""

    CONTRIBUTING = "contributing"
    NEUTRAL = "neutral"
    FREE_RIDER = "free_rider"


class FreeRiderError(Exception):
    """Base exception for free-rider detection errors."""


@dataclass
class BandwidthAccount:
    """Tracks bandwidth contributed to and received from a peer."""

    peer_id: str
    bytes_sent: int = 0
    bytes_received: int = 0
    chunks_sent: int = 0
    chunks_received: int = 0
    last_activity: int = field(default_factory=lambda: int(time.time()))

    @property
    def ratio(self) -> float:
        """Ratio of bytes sent to bytes received.

        > 1.0 means the peer contributes more than it receives.
        < 1.0 means the peer receives more than it contributes.
        """
        if self.bytes_received == 0:
            return 1.0 if self.bytes_sent > 0 else 0.0
        return self.bytes_sent / self.bytes_received

    def record_sent(self, bytes_count: int) -> None:
        """Record bytes sent to this peer."""
        self.bytes_sent += bytes_count
        self.chunks_sent += 1
        self.last_activity = int(time.time())

    def record_received(self, bytes_count: int) -> None:
        """Record bytes received from this peer."""
        self.bytes_received += bytes_count
        self.chunks_received += 1
        self.last_activity = int(time.time())


@dataclass
class TitForTatStats:
    """Statistics for tit-for-tat monitoring."""

    total_peers: int = 0
    contributing_peers: int = 0
    neutral_peers: int = 0
    free_riders: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    total_chunks_sent: int = 0
    total_chunks_received: int = 0
    disconnected_free_riders: int = 0

    @property
    def overall_ratio(self) -> float:
        """Overall sent/received ratio across all peers."""
        if self.total_bytes_received == 0:
            return 1.0 if self.total_bytes_sent > 0 else 0.0
        return self.total_bytes_sent / self.total_bytes_received


class TitForTatManager:
    """Manages tit-for-tat bandwidth accounting between peers.

    Tracks per-peer bandwidth contributions, classifies peers as
    contributing/neutral/free-riders, and provides prioritization
    for chunk delivery.
    """

    def __init__(
        self,
        free_rider_threshold: float = 0.1,
        contributing_threshold: float = 0.8,
        free_rider_timeout_seconds: int = 300,
        max_free_rider_warnings: int = 3,
    ) -> None:
        self.free_rider_threshold = free_rider_threshold
        self.contributing_threshold = contributing_threshold
        self.free_rider_timeout_seconds = free_rider_timeout_seconds
        self.max_free_rider_warnings = max_free_rider_warnings
        self._accounts: dict[str, BandwidthAccount] = {}
        self._free_rider_warnings: dict[str, int] = {}
        self._disconnected: set[str] = set()
        self._stats = TitForTatStats()

    @property
    def stats(self) -> TitForTatStats:
        """Current tit-for-tat statistics."""
        self._update_stats()
        return self._stats

    @property
    def accounts(self) -> dict[str, BandwidthAccount]:
        """All bandwidth accounts keyed by peer ID."""
        return self._accounts

    def register_peer(self, peer_id: str) -> BandwidthAccount:
        """Register a new peer for bandwidth tracking."""
        if peer_id not in self._accounts:
            self._accounts[peer_id] = BandwidthAccount(peer_id=peer_id)
        return self._accounts[peer_id]

    def record_sent(self, peer_id: str, bytes_count: int) -> None:
        """Record bytes sent to a peer."""
        account = self.register_peer(peer_id)
        account.record_sent(bytes_count)

    def record_received(self, peer_id: str, bytes_count: int) -> None:
        """Record bytes received from a peer."""
        account = self.register_peer(peer_id)
        account.record_received(bytes_count)

    def get_contribution(self, peer_id: str) -> PeerContribution:
        """Classify a peer's contribution level."""
        account = self._accounts.get(peer_id)
        if not account:
            return PeerContribution.NEUTRAL

        # Check for inactivity timeout
        if (
            time.time() - account.last_activity > self.free_rider_timeout_seconds
            and account.bytes_received > 0
            and account.bytes_sent == 0
        ):
            return PeerContribution.FREE_RIDER

        ratio = account.ratio
        if ratio >= self.contributing_threshold:
            return PeerContribution.CONTRIBUTING
        if ratio >= self.free_rider_threshold:
            return PeerContribution.NEUTRAL
        return PeerContribution.FREE_RIDER

    def should_prioritize(self, peer_id: str) -> bool:
        """Whether a peer should get priority bandwidth.

        Contributing peers get priority. Free-riders are deprioritized.
        """
        contribution = self.get_contribution(peer_id)
        return contribution != PeerContribution.FREE_RIDER

    def check_free_rider(self, peer_id: str) -> bool:
        """Check if a peer is a free-rider and warn them.

        Returns True if the peer should be disconnected.
        """
        if self.get_contribution(peer_id) != PeerContribution.FREE_RIDER:
            return False

        warnings = self._free_rider_warnings.get(peer_id, 0) + 1
        self._free_rider_warnings[peer_id] = warnings

        if warnings >= self.max_free_rider_warnings:
            self._disconnected.add(peer_id)
            self._stats.disconnected_free_riders += 1
            return True
        return False

    def is_disconnected(self, peer_id: str) -> bool:
        """Whether a peer has been disconnected for free-riding."""
        return peer_id in self._disconnected

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer's bandwidth tracking."""
        self._accounts.pop(peer_id, None)
        self._free_rider_warnings.pop(peer_id, None)
        self._disconnected.discard(peer_id)

    def get_priority_order(self, peer_ids: list[str]) -> list[str]:
        """Sort peers by delivery priority.

        Contributing peers first, then neutral, then free-riders.
        """

        def sort_key(peer_id: str) -> tuple[int, float]:
            contribution = self.get_contribution(peer_id)
            if contribution == PeerContribution.CONTRIBUTING:
                return (0, 0.0)
            if contribution == PeerContribution.NEUTRAL:
                return (1, 0.0)
            return (2, 0.0)

        return sorted(peer_ids, key=sort_key)

    def _update_stats(self) -> None:
        """Refresh tit-for-tat statistics."""
        self._stats.total_peers = len(self._accounts)
        self._stats.contributing_peers = sum(
            1 for p in self._accounts if self.get_contribution(p) == PeerContribution.CONTRIBUTING
        )
        self._stats.neutral_peers = sum(
            1 for p in self._accounts if self.get_contribution(p) == PeerContribution.NEUTRAL
        )
        self._stats.free_riders = sum(
            1 for p in self._accounts if self.get_contribution(p) == PeerContribution.FREE_RIDER
        )
        self._stats.total_bytes_sent = sum(a.bytes_sent for a in self._accounts.values())
        self._stats.total_bytes_received = sum(a.bytes_received for a in self._accounts.values())
        self._stats.total_chunks_sent = sum(a.chunks_sent for a in self._accounts.values())
        self._stats.total_chunks_received = sum(a.chunks_received for a in self._accounts.values())
