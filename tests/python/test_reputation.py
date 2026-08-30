"""Tests for the QLive off-chain relay reputation tracker."""

import hashlib

import pytest

from qlive.proof import BandwidthReceipt, ReceiptState
from qlive.reputation import (
    DAY_MS,
    RelayReputationTracker,
    ReputationError,
    RelayReputation,
)

MB = 1024 * 1024


@pytest.fixture
def stream_id() -> bytes:
    """A valid 32-byte stream ID."""
    return hashlib.sha256(b"test-stream").digest()


@pytest.fixture
def other_stream_id() -> bytes:
    """A second stream ID for diversity tests."""
    return hashlib.sha256(b"other-stream").digest()


def make_receipt(
    relay: str,
    downstream: str,
    stream_id: bytes,
    bytes_relayed: int,
    timestamp: int = 0,
    state: ReceiptState = ReceiptState.VERIFIED,
    start_sequence: int = 1,
    end_sequence: int = 10,
) -> BandwidthReceipt:
    """Build a signed-less receipt with an explicit lifecycle state."""
    receipt = BandwidthReceipt(
        relay_node_id=relay,
        downstream_node_id=downstream,
        stream_id=stream_id,
        bytes_relayed=bytes_relayed,
        timestamp=timestamp,
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )
    receipt.state = state
    return receipt


class TestRelayReputation:
    def test_init(self):
        rep = RelayReputation(relay_node_id="relay-1")
        assert rep.relay_node_id == "relay-1"
        assert rep.score == 0.0
        assert rep.raw_credit == 0.0
        assert rep.bytes_total == 0
        assert rep.downstream_count == 0
        assert rep.stream_count == 0


class TestRelayReputationTracker:
    def test_unknown_relay_score_is_zero(self, stream_id):
        tracker = RelayReputationTracker(dispute_window_seconds=0)
        assert tracker.score("ghost", now_ms=0) == 0.0
        assert tracker.get_reputation("ghost", now_ms=0) is None

    def test_consider_verified_receipt_counts(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        receipt = make_receipt("relay-1", "down-1", stream_id, MB)
        assert tracker.consider_receipt(receipt, now_ms=0) is True

        rep = tracker.get_reputation("relay-1", now_ms=0)
        assert rep is not None
        assert rep.downstream_count == 1
        assert rep.stream_count == 1
        assert rep.bytes_total == MB
        assert rep.raw_credit == 1.0  # 1 MB × credit_per_mb=1.0
        assert rep.score == 1.0  # diversity factor 1.0 (targets are 1)

    def test_consider_redeemed_receipt_counts(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        receipt = make_receipt(
            "relay-1", "down-1", stream_id, MB, state=ReceiptState.REDEEMED
        )
        assert tracker.consider_receipt(receipt, now_ms=0) is True
        assert tracker.score("relay-1", now_ms=0) > 0

    def test_ignores_pending_and_rejected(self, stream_id):
        tracker = RelayReputationTracker(dispute_window_seconds=0)
        pending = make_receipt(
            "relay-1", "down-1", stream_id, MB, state=ReceiptState.PENDING
        )
        rejected = make_receipt(
            "relay-1", "down-1", stream_id, MB, state=ReceiptState.REJECTED
        )
        assert tracker.consider_receipt(pending, now_ms=0) is False
        assert tracker.consider_receipt(rejected, now_ms=0) is False
        assert tracker.score("relay-1", now_ms=0) == 0.0

    def test_respects_dispute_window(self, stream_id):
        tracker = RelayReputationTracker(dispute_window_seconds=86400)
        young = make_receipt("relay-1", "down-1", stream_id, MB, timestamp=0)
        assert tracker.consider_receipt(young, now_ms=1_000) is False  # 1s old
        assert tracker.score("relay-1", now_ms=1_000) == 0.0

        # A distinct receipt observed just past the 24h window is eligible.
        mature = make_receipt("relay-1", "down-1", stream_id, MB, timestamp=0)
        now = 86_400_000 + 1
        assert tracker.consider_receipt(mature, now_ms=now) is True
        assert tracker.score("relay-1", now_ms=now) > 0

    def test_same_receipt_not_double_counted(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        receipt = make_receipt("relay-1", "down-1", stream_id, MB)
        assert tracker.consider_receipt(receipt, now_ms=0) is True
        assert tracker.consider_receipt(receipt, now_ms=0) is False
        rep = tracker.get_reputation("relay-1", now_ms=0)
        assert rep.raw_credit == 1.0
        assert rep.bytes_total == MB

    def test_distinct_instances_same_claim_deduped(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        first = make_receipt("relay-1", "down-1", stream_id, MB)
        second = make_receipt("relay-1", "down-1", stream_id, MB)
        # Different objects but identical claim contents -> counted once.
        assert tracker.consider_receipt(first, now_ms=0) is True
        assert tracker.consider_receipt(second, now_ms=0) is False
        rep = tracker.get_reputation("relay-1", now_ms=0)
        assert rep.raw_credit == 1.0

    def test_capped_contribution_per_receipt(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
            max_contribution_per_receipt=2.0,
        )
        huge = make_receipt("relay-1", "down-1", stream_id, MB * 100)  # 100 MB
        assert tracker.consider_receipt(huge, now_ms=0) is True
        rep = tracker.get_reputation("relay-1", now_ms=0)
        assert rep.raw_credit == 2.0
        assert rep.score == 2.0

    def test_max_score_cap(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
            max_score=10.0,
            max_contribution_per_receipt=5.0,
        )
        for i in range(5):
            tracker.consider_receipt(
                make_receipt(
                    "relay-1",
                    "down-1",
                    stream_id,
                    MB * 10,
                    start_sequence=i + 1,
                    end_sequence=i + 1,
                ),
                now_ms=0,
            )
        assert tracker.score("relay-1", now_ms=0) == 10.0

    def test_diversity_rewards_reaching_more_peers_and_streams(
        self, stream_id, other_stream_id
    ):
        # Concentrated: 2 MB to a single downstream on a single stream.
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=2,
            stream_target=2,
        )
        tracker.consider_receipt(
            make_receipt("concentrated", "down-1", stream_id, MB * 2),
            now_ms=0,
        )
        # Diversified: 2 MB split across 2 downstreams and 2 streams.
        tracker.consider_receipt(
            make_receipt("diversified", "down-1", stream_id, MB),
            now_ms=0,
        )
        tracker.consider_receipt(
            make_receipt("diversified", "down-2", other_stream_id, MB),
            now_ms=0,
        )

        # Same total bytes, but diversity lifts the score.
        concentrated = tracker.score("concentrated", now_ms=0)  # 0.25 × 2 = 0.5
        diversified = tracker.score("diversified", now_ms=0)  # 1.0 × 2 = 2.0
        assert concentrated == pytest.approx(0.5)
        assert diversified == pytest.approx(2.0)
        assert diversified > concentrated

    def test_decay_over_time(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
            decay_per_day=0.5,
        )
        tracker.consider_receipt(
            make_receipt("relay-1", "down-1", stream_id, MB), now_ms=0
        )
        score_now = tracker.score("relay-1", now_ms=0)
        assert score_now == pytest.approx(1.0)

        # After 4 days the score reduces by 0.5**4.
        score_later = tracker.score("relay-1", now_ms=4 * DAY_MS)
        assert score_later == pytest.approx(score_now * 0.5**4, rel=1e-6)

    def test_priority_order_by_score(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        tracker.consider_receipt(make_receipt("low", "d", stream_id, MB), now_ms=0)
        tracker.consider_receipt(make_receipt("high", "d", stream_id, MB * 100), now_ms=0)
        tracker.consider_receipt(make_receipt("mid", "d", stream_id, MB * 5), now_ms=0)

        assert tracker.order(["low", "high", "mid"], now_ms=0) == ["high", "mid", "low"]
        assert tracker.get_priority_order(["low", "high", "mid"], now_ms=0) == [
            "high",
            "mid",
            "low",
        ]

    def test_import_from_manager(self, stream_id):
        from qlive.proof import ProofOfRelayManager

        manager = ProofOfRelayManager()
        confirmed_1 = manager.create_receipt("relay-1", "down-1", stream_id, MB)
        confirmed_1.state = ReceiptState.REDEEMED
        confirmed_2 = manager.create_receipt("relay-1", "down-2", stream_id, MB)
        confirmed_2.state = ReceiptState.REDEEMED
        pending = manager.create_receipt("relay-2", "down-1", stream_id, MB)
        pending.state = ReceiptState.PENDING  # ignored

        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=2,
            stream_target=1,
        )
        added = tracker.import_from_manager(manager)
        assert added == 2
        assert "relay-1" in tracker.reputations
        assert "relay-2" not in tracker.reputations
        assert tracker.stats.total_relays == 1

    def test_remove_relay_and_clear(self, stream_id):
        tracker = RelayReputationTracker(
            dispute_window_seconds=0,
            downstream_target=1,
            stream_target=1,
        )
        tracker.consider_receipt(
            make_receipt("relay-1", "down-1", stream_id, MB), now_ms=0
        )
        assert tracker.score("relay-1", now_ms=0) > 0

        tracker.remove_relay("relay-1")
        assert tracker.score("relay-1", now_ms=0) == 0.0

        # A *new* claim (different sequence range) counts and re-records the relay.
        tracker.consider_receipt(
            make_receipt(
                "relay-1", "down-1", stream_id, MB, start_sequence=2, end_sequence=2
            ),
            now_ms=0,
        )
        assert "relay-1" in tracker.reputations
        tracker.clear()
        assert tracker.reputations == {}

    def test_invalid_constructor_params(self):
        with pytest.raises(ReputationError):
            RelayReputationTracker(decay_per_day=0.0)
        with pytest.raises(ReputationError):
            RelayReputationTracker(decay_per_day=1.5)
        with pytest.raises(ReputationError):
            RelayReputationTracker(max_score=-1)
        with pytest.raises(ReputationError):
            RelayReputationTracker(max_contribution_per_receipt=0)
        with pytest.raises(ReputationError):
            RelayReputationTracker(downstream_target=0)
        with pytest.raises(ReputationError):
            RelayReputationTracker(credit_per_mb=0)