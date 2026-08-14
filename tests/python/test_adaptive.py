"""Tests for the QLive adaptive bitrate control."""

import pytest

from qlive.adaptive import (
    AdaptiveBitrateController,
    BitrateAction,
    BitrateLadder,
)
from qlive.buffer import BufferState


class TestBitrateLadder:
    def test_default_ladder(self):
        ladder = BitrateLadder()
        assert ladder.bitrates == [1000, 2000, 3000, 4500, 6000]
        assert ladder.lowest == 1000
        assert ladder.highest == 6000

    def test_custom_ladder_sorted(self):
        ladder = BitrateLadder(bitrates=[3000, 1000, 2000])
        assert ladder.bitrates == [1000, 2000, 3000]

    def test_empty_ladder(self):
        with pytest.raises(ValueError):
            BitrateLadder(bitrates=[])

    def test_index_of_exact(self):
        ladder = BitrateLadder()
        assert ladder.index_of(3000) == 2

    def test_index_of_nearest(self):
        ladder = BitrateLadder()
        assert ladder.index_of(2500) == 1  # Nearest to 2000

    def test_upgrade(self):
        ladder = BitrateLadder()
        assert ladder.upgrade(1000) == 2000
        assert ladder.upgrade(3000) == 4500

    def test_upgrade_at_highest(self):
        ladder = BitrateLadder()
        assert ladder.upgrade(6000) == 6000

    def test_downgrade(self):
        ladder = BitrateLadder()
        assert ladder.downgrade(6000) == 4500
        assert ladder.downgrade(3000) == 2000

    def test_downgrade_at_lowest(self):
        ladder = BitrateLadder()
        assert ladder.downgrade(1000) == 1000


class TestAdaptiveBitrateController:
    def test_init_defaults(self):
        controller = AdaptiveBitrateController()
        assert controller.current_bitrate == 1000
        assert controller.upgrade_cooldown_seconds == 10
        assert controller.downgrade_cooldown_seconds == 5
        assert controller.downgrade_count == 0
        assert controller.upgrade_count == 0

    def test_init_custom(self):
        ladder = BitrateLadder(bitrates=[500, 1000, 2000])
        controller = AdaptiveBitrateController(
            ladder=ladder, initial_bitrate=1000
        )
        assert controller.current_bitrate == 1000

    def test_evaluate_stalling_downgrade(self):
        controller = AdaptiveBitrateController()
        action = controller.evaluate(BufferState.STALLING, now=10.0)
        assert action == BitrateAction.DOWNGRADE

    def test_evaluate_stalling_cooldown(self):
        controller = AdaptiveBitrateController(initial_bitrate=3000)
        # First downgrade at t=10
        controller.apply(BitrateAction.DOWNGRADE, now=10.0)
        # Stalling again before cooldown
        action = controller.evaluate(BufferState.STALLING, now=12.0)
        assert action == BitrateAction.STAY

    def test_evaluate_healthy_stay_initial(self):
        controller = AdaptiveBitrateController()
        action = controller.evaluate(BufferState.HEALTHY, now=10.0)
        assert action == BitrateAction.STAY

    def test_evaluate_healthy_upgrade_after_cooldown(self):
        controller = AdaptiveBitrateController()
        # First healthy observation
        controller.evaluate(BufferState.HEALTHY, now=10.0)
        # Still healthy after cooldown
        action = controller.evaluate(BufferState.HEALTHY, now=25.0)
        assert action == BitrateAction.UPGRADE

    def test_evaluate_filling_stay(self):
        controller = AdaptiveBitrateController()
        action = controller.evaluate(BufferState.FILLING, now=10.0)
        assert action == BitrateAction.STAY

    def test_apply_downgrade(self):
        controller = AdaptiveBitrateController()
        new_bitrate = controller.apply(BitrateAction.DOWNGRADE, now=10.0)
        assert new_bitrate == 1000  # Already at lowest
        assert controller.downgrade_count == 0

    def test_apply_downgrade_from_middle(self):
        controller = AdaptiveBitrateController(initial_bitrate=3000)
        new_bitrate = controller.apply(BitrateAction.DOWNGRADE, now=10.0)
        assert new_bitrate == 2000
        assert controller.downgrade_count == 1

    def test_apply_upgrade(self):
        controller = AdaptiveBitrateController(initial_bitrate=1000)
        new_bitrate = controller.apply(BitrateAction.UPGRADE, now=10.0)
        assert new_bitrate == 2000
        assert controller.upgrade_count == 1

    def test_apply_upgrade_at_highest(self):
        controller = AdaptiveBitrateController(initial_bitrate=6000)
        new_bitrate = controller.apply(BitrateAction.UPGRADE, now=10.0)
        assert new_bitrate == 6000
        assert controller.upgrade_count == 0

    def test_apply_stay(self):
        controller = AdaptiveBitrateController(initial_bitrate=3000)
        new_bitrate = controller.apply(BitrateAction.STAY, now=10.0)
        assert new_bitrate == 3000
        assert controller.upgrade_count == 0
        assert controller.downgrade_count == 0

    def test_full_cycle(self):
        """Test the full adaptive cycle: downgrade then upgrade."""
        controller = AdaptiveBitrateController(initial_bitrate=4500)

        # Stalling -> downgrade to 3000
        action = controller.evaluate(BufferState.STALLING, now=10.0)
        assert action == BitrateAction.DOWNGRADE
        assert controller.apply(action, now=10.0) == 3000

        # Healthy for a while -> upgrade back to 4500
        controller.evaluate(BufferState.HEALTHY, now=20.0)
        action = controller.evaluate(BufferState.HEALTHY, now=35.0)
        assert action == BitrateAction.UPGRADE
        assert controller.apply(action, now=35.0) == 4500

        assert controller.downgrade_count == 1
        assert controller.upgrade_count == 1

    def test_reset(self):
        controller = AdaptiveBitrateController(initial_bitrate=3000)
        controller.apply(BitrateAction.DOWNGRADE, now=10.0)
        controller.apply(BitrateAction.UPGRADE, now=20.0)
        controller.reset()
        assert controller.current_bitrate == 1000
        assert controller.downgrade_count == 0
        assert controller.upgrade_count == 0