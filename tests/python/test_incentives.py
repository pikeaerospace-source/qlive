"""Tests for the QLive tit-for-tat data swapping."""

import time

import pytest

from qlive.incentives import (
    BandwidthAccount,
    PeerContribution,
    TitForTatManager,
    TitForTatStats,
)


class TestBandwidthAccount:
    def test_init(self):
        account = BandwidthAccount(peer_id="peer-1")
        assert account.peer_id == "peer-1"
        assert account.bytes_sent == 0
        assert account.bytes_received == 0
        assert account.chunks_sent == 0
        assert account.chunks_received == 0

    def test_ratio_no_activity(self):
        account = BandwidthAccount(peer_id="peer-1")
        assert account.ratio == 0.0

    def test_ratio_sent_only(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_sent(1000)
        assert account.ratio == 1.0

    def test_ratio_balanced(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_sent(1000)
        account.record_received(1000)
        assert account.ratio == 1.0

    def test_ratio_contributing(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_sent(2000)
        account.record_received(1000)
        assert account.ratio == 2.0

    def test_ratio_free_rider(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_received(1000)
        assert account.ratio == 0.0

    def test_record_sent(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_sent(500)
        assert account.bytes_sent == 500
        assert account.chunks_sent == 1

    def test_record_received(self):
        account = BandwidthAccount(peer_id="peer-1")
        account.record_received(500)
        assert account.bytes_received == 500
        assert account.chunks_received == 1


class TestTitForTatStats:
    def test_init(self):
        stats = TitForTatStats()
        assert stats.total_peers == 0
        assert stats.contributing_peers == 0
        assert stats.neutral_peers == 0
        assert stats.free_riders == 0
        assert stats.total_bytes_sent == 0
        assert stats.total_bytes_received == 0
        assert stats.disconnected_free_riders == 0
        assert stats.overall_ratio == 0.0

    def test_overall_ratio(self):
        stats = TitForTatStats(total_bytes_sent=2000, total_bytes_received=1000)
        assert stats.overall_ratio == 2.0


class TestTitForTatManager:
    def test_init(self):
        manager = TitForTatManager()
        assert manager.free_rider_threshold == 0.1
        assert manager.contributing_threshold == 0.8
        assert manager.free_rider_timeout_seconds == 300
        assert manager.max_free_rider_warnings == 3
        assert manager.accounts == {}
        assert manager.stats.total_peers == 0

    def test_register_peer(self):
        manager = TitForTatManager()
        account = manager.register_peer("peer-1")
        assert account.peer_id == "peer-1"
        assert "peer-1" in manager.accounts

    def test_register_peer_idempotent(self):
        manager = TitForTatManager()
        account1 = manager.register_peer("peer-1")
        account2 = manager.register_peer("peer-1")
        assert account1 is account2

    def test_record_sent(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 1000)
        assert manager.accounts["peer-1"].bytes_sent == 1000

    def test_record_received(self):
        manager = TitForTatManager()
        manager.record_received("peer-1", 1000)
        assert manager.accounts["peer-1"].bytes_received == 1000

    def test_get_contribution_unknown_peer(self):
        manager = TitForTatManager()
        assert manager.get_contribution("unknown") == PeerContribution.NEUTRAL

    def test_get_contribution_contributing(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 2000)
        manager.record_received("peer-1", 1000)
        assert manager.get_contribution("peer-1") == PeerContribution.CONTRIBUTING

    def test_get_contribution_neutral(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 500)
        manager.record_received("peer-1", 1000)
        assert manager.get_contribution("peer-1") == PeerContribution.NEUTRAL

    def test_get_contribution_free_rider(self):
        manager = TitForTatManager()
        manager.record_received("peer-1", 1000)
        assert manager.get_contribution("peer-1") == PeerContribution.FREE_RIDER

    def test_get_contribution_inactive_free_rider(self):
        manager = TitForTatManager(free_rider_timeout_seconds=1)
        manager.record_received("peer-1", 1000)
        # Simulate inactivity
        manager.accounts["peer-1"].last_activity = int(time.time()) - 10
        assert manager.get_contribution("peer-1") == PeerContribution.FREE_RIDER

    def test_should_prioritize_contributing(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 2000)
        manager.record_received("peer-1", 1000)
        assert manager.should_prioritize("peer-1") is True

    def test_should_prioritize_free_rider(self):
        manager = TitForTatManager()
        manager.record_received("peer-1", 1000)
        assert manager.should_prioritize("peer-1") is False

    def test_check_free_rider_warning(self):
        manager = TitForTatManager()
        manager.record_received("peer-1", 1000)
        assert manager.check_free_rider("peer-1") is False  # First warning
        assert manager.check_free_rider("peer-1") is False  # Second warning

    def test_check_free_rider_disconnect(self):
        manager = TitForTatManager(max_free_rider_warnings=2)
        manager.record_received("peer-1", 1000)
        manager.check_free_rider("peer-1")
        assert manager.check_free_rider("peer-1") is True  # Disconnected
        assert manager.is_disconnected("peer-1") is True
        assert manager.stats.disconnected_free_riders == 1

    def test_check_free_rider_not_free_rider(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 2000)
        manager.record_received("peer-1", 1000)
        assert manager.check_free_rider("peer-1") is False
        assert manager.is_disconnected("peer-1") is False

    def test_remove_peer(self):
        manager = TitForTatManager()
        manager.record_received("peer-1", 1000)
        manager.check_free_rider("peer-1")
        manager.remove_peer("peer-1")
        assert "peer-1" not in manager.accounts
        assert manager.is_disconnected("peer-1") is False

    def test_get_priority_order(self):
        manager = TitForTatManager()
        # Contributing peer
        manager.record_sent("peer-1", 2000)
        manager.record_received("peer-1", 1000)
        # Neutral peer
        manager.record_sent("peer-2", 500)
        manager.record_received("peer-2", 1000)
        # Free rider
        manager.record_received("peer-3", 1000)

        order = manager.get_priority_order(["peer-3", "peer-1", "peer-2"])
        assert order[0] == "peer-1"  # Contributing first
        assert order[1] == "peer-2"  # Neutral second
        assert order[2] == "peer-3"  # Free rider last

    def test_stats(self):
        manager = TitForTatManager()
        manager.record_sent("peer-1", 2000)
        manager.record_received("peer-1", 1000)
        manager.record_sent("peer-2", 500)
        manager.record_received("peer-2", 1000)
        manager.record_received("peer-3", 1000)

        stats = manager.stats
        assert stats.total_peers == 3
        assert stats.contributing_peers == 1
        assert stats.neutral_peers == 1
        assert stats.free_riders == 1
        assert stats.total_bytes_sent == 2500
        assert stats.total_bytes_received == 3000
        assert stats.total_chunks_sent == 2
        assert stats.total_chunks_received == 3