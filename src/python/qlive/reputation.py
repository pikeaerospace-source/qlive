"""QLive off-chain relay reputation tracking.

Derives a per-node reputation score from confirmed proof-of-relay bandwidth
receipts (phase 1 of the minting/reputation integration — see
docs/MINTING-INTEGRATION.md). The score is intended to drive *local* decisions
— routing priority and fair bounty ordering — and involves no Qortal Core or
chain writes.

Gaming resistance (docs/MINTING-INTEGRATION.md §A and SECURITY-MODEL.md §3):

- **Time-weighted decay** — scores fade over time, so a one-off boost does not
  linger.
- **Diversity weighting** — a relay must serve *distinct* downstream peers
  across *distinct* streams to reach full score, so a small colluding cohort
  cannot inflate it.
- **Capped contribution** — per-receipt credit is capped and the overall score
  is bounded (mirrors the bounded bounty pool).
- **Dispute window** — receipts count toward reputation only once they are
  confirmed and past the redemption/dispute window.
- **Dedup** — the same receipt object is never counted twice.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from qlive.proof import BandwidthReceipt, ReceiptState

MB = 1024 * 1024
DAY_MS = 86_400_000


class ReputationError(Exception):
    """Base exception for reputation-tracking errors."""


@dataclass
class RelayReputation:
    """Accumulated reputation for a single relay node."""

    relay_node_id: str
    score: float = 0.0
    raw_credit: float = 0.0
    bytes_total: int = 0
    distinct_downstreams: set[str] = field(default_factory=set)
    distinct_streams: set[bytes] = field(default_factory=set)
    last_update_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def downstream_count(self) -> int:
        """Number of distinct downstream peers served."""
        return len(self.distinct_downstreams)

    @property
    def stream_count(self) -> int:
        """Number of distinct streams served."""
        return len(self.distinct_streams)


@dataclass
class ReputationStats:
    """Statistics for reputation tracking."""

    total_relays: int = 0
    mean_score: float = 0.0
    total_bytes_proven: int = 0


class RelayReputationTracker:
    """Tracks and scores relay reputation from confirmed bandwidth receipts.

    Receipts are accepted via :meth:`consider_receipt` (or batched from a
    ``ProofOfRelayManager``). Only receipts that are confirmed (``VERIFIED`` or
    ``REDEEMED``) and mature (past the dispute window) contribute; each receipt
    is counted at most once.
    """

    def __init__(
        self,
        *,
        decay_per_day: float = 0.5,
        max_score: float = 1000.0,
        max_contribution_per_receipt: float = 100.0,
        downstream_target: int = 4,
        stream_target: int = 2,
        dispute_window_seconds: int = 86400,  # 24h dispute window
        credit_per_mb: float = 1.0,
    ) -> None:
        if not 0.0 < decay_per_day <= 1.0:
            raise ReputationError("decay_per_day must be in (0, 1]")
        if max_score <= 0:
            raise ReputationError("max_score must be positive")
        if max_contribution_per_receipt <= 0:
            raise ReputationError("max_contribution_per_receipt must be positive")
        if downstream_target < 1 or stream_target < 1:
            raise ReputationError("diversity targets must be >= 1")
        if credit_per_mb <= 0:
            raise ReputationError("credit_per_mb must be positive")

        self.decay_per_day = decay_per_day
        self.max_score = max_score
        self.max_contribution_per_receipt = max_contribution_per_receipt
        self.downstream_target = downstream_target
        self.stream_target = stream_target
        self.dispute_window_seconds = dispute_window_seconds
        self.credit_per_mb = credit_per_mb

        self._reps: dict[str, RelayReputation] = {}
        self._seen: set[bytes] = set()
        self._stats = ReputationStats()

    @property
    def reputations(self) -> dict[str, RelayReputation]:
        """All tracked relay reputations keyed by relay node ID."""
        return self._reps

    @property
    def stats(self) -> ReputationStats:
        """Current reputation statistics."""
        self._stats.total_relays = len(self._reps)
        scores = [r.score for r in self._reps.values()]
        self._stats.mean_score = sum(scores) / len(scores) if scores else 0.0
        self._stats.total_bytes_proven = sum(r.bytes_total for r in self._reps.values())
        return self._stats

    def _eligible(self, receipt: BandwidthReceipt, now_ms: int) -> bool:
        """Whether a receipt may contribute to reputation."""
        if receipt.state not in (ReceiptState.VERIFIED, ReceiptState.REDEEMED):
            return False
        if self.dispute_window_seconds > 0:
            age_ms = now_ms - receipt.timestamp
            if age_ms < self.dispute_window_seconds * 1000:
                return False
        return True

    def consider_receipt(
        self, receipt: BandwidthReceipt, *, now_ms: int | None = None
    ) -> bool:
        """Consider a confirmed receipt for reputation.

        Returns ``True`` if the receipt contributed (eligible, mature, and not
        already counted).
        """
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        if not self._eligible(receipt, now):
            return False
        # Dedup by receipt *contents*, not object identity: ``id()`` is reused
        # after GC, and two instances with identical ``signing_data`` represent
        # the same claim.
        claim = receipt.signing_data
        if claim in self._seen:
            return False
        self._seen.add(claim)

        rep = self._reps.setdefault(
            receipt.relay_node_id,
            RelayReputation(receipt.relay_node_id, last_update_ms=now),
        )
        # Decay the existing (pre-this-receipt) credit/score for elapsed time.
        self._decay(rep, now)

        rep.distinct_downstreams.add(receipt.downstream_node_id)
        rep.distinct_streams.add(receipt.stream_id)
        rep.bytes_total += receipt.bytes_relayed

        contribution = min(
            self.max_contribution_per_receipt,
            receipt.bytes_relayed / MB * self.credit_per_mb,
        )
        rep.raw_credit += contribution
        rep.score = self._computed_score(rep)
        rep.last_update_ms = now
        return True

    def get_reputation(
        self, relay_id: str, *, now_ms: int | None = None
    ) -> RelayReputation | None:
        """Return a relay's reputation, applying decay up to ``now``."""
        rep = self._reps.get(relay_id)
        if rep is None:
            return None
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        self._decay(rep, now)
        rep.score = self._computed_score(rep)
        return rep

    def score(self, relay_id: str, *, now_ms: int | None = None) -> float:
        """Current reputation score for a relay (0.0 if unknown)."""
        rep = self.get_reputation(relay_id, now_ms=now_ms)
        return rep.score if rep else 0.0

    def order(self, relay_ids: list[str], *, now_ms: int | None = None) -> list[str]:
        """Sort relays by descending reputation (routing / bounty ordering)."""
        ranked = [(self.score(r, now_ms=now_ms), r) for r in relay_ids]
        ranked.sort(key=lambda pair: (-pair[0], pair[1]))
        return [r for _, r in ranked]

    def get_priority_order(
        self, relay_ids: list[str], *, now_ms: int | None = None
    ) -> list[str]:
        """Alias for :meth:`order` (mirrors ``TitForTatManager`` naming)."""
        return self.order(relay_ids, now_ms=now_ms)

    def import_from_manager(
        self, manager: object, *, now_ms: int | None = None
    ) -> int:
        """Consider all confirmed receipts from a ``ProofOfRelayManager``.

        Returns the number of new receipts counted.
        """
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        added = 0
        for receipt in manager.receipts:  # type: ignore[attr-defined]
            if self.consider_receipt(receipt, now_ms=now):
                added += 1
        return added

    def remove_relay(self, relay_id: str) -> None:
        """Drop a relay from reputation tracking."""
        self._reps.pop(relay_id, None)

    def clear(self) -> None:
        """Reset all reputation state."""
        self._reps.clear()
        self._seen.clear()

    def _decay(self, rep: RelayReputation, now_ms: int) -> None:
        """Apply exponential time decay to an existing reputation."""
        elapsed_days = max(0.0, (now_ms - rep.last_update_ms) / DAY_MS)
        factor = self.decay_per_day**elapsed_days
        rep.raw_credit *= factor
        rep.score *= factor
        rep.last_update_ms = now_ms

    def _diversity(self, rep: RelayReputation) -> float:
        """Diversity multiplier in [0, 1] rewarding breadth of service."""
        downstream_factor = min(1.0, rep.downstream_count / self.downstream_target)
        stream_factor = min(1.0, rep.stream_count / self.stream_target)
        return downstream_factor * stream_factor

    def _computed_score(self, rep: RelayReputation) -> float:
        """Capped, diversity-weighted score from the (decayed) raw credit."""
        return min(self.max_score, rep.raw_credit * self._diversity(rep))