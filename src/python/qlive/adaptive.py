"""QLive adaptive bitrate control.

Implements graceful degradation when the buffer is under pressure
(protocol spec section 6.4). When the buffer enters a stalling state,
the viewer requests a lower bitrate from the broadcaster. When the
buffer is healthy, the viewer can request a higher bitrate.

This module provides the bitrate ladder and the logic for selecting
the appropriate bitrate based on buffer health.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from qlive.buffer import BufferState


class BitrateAction(Enum):
    """Actions the viewer can request based on buffer health."""

    STAY = "stay"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"


@dataclass
class BitrateLadder:
    """A ladder of available bitrates for adaptive streaming.

    Bitrates are ordered from lowest to highest. The viewer selects
    a bitrate from this ladder based on buffer health.
    """

    bitrates: list[int] = field(
        default_factory=lambda: [1000, 2000, 3000, 4500, 6000]
    )

    def __post_init__(self) -> None:
        if not self.bitrates:
            raise ValueError("Bitrate ladder cannot be empty")
        # Ensure sorted ascending
        self.bitrates = sorted(self.bitrates)

    @property
    def lowest(self) -> int:
        """Lowest available bitrate (kbps)."""
        return self.bitrates[0]

    @property
    def highest(self) -> int:
        """Highest available bitrate (kbps)."""
        return self.bitrates[-1]

    def index_of(self, bitrate: int) -> int:
        """Get the index of a bitrate in the ladder."""
        try:
            return self.bitrates.index(bitrate)
        except ValueError:
            # Find nearest
            return min(
                range(len(self.bitrates)),
                key=lambda i: abs(self.bitrates[i] - bitrate),
            )

    def upgrade(self, current: int) -> int:
        """Get the next higher bitrate, or stay at the highest."""
        idx = self.index_of(current)
        return self.bitrates[min(idx + 1, len(self.bitrates) - 1)]

    def downgrade(self, current: int) -> int:
        """Get the next lower bitrate, or stay at the lowest."""
        idx = self.index_of(current)
        return self.bitrates[max(idx - 1, 0)]


class AdaptiveBitrateController:
    """Controls bitrate selection based on buffer health.

    Uses a hysteresis approach to avoid oscillation:
    - Downgrade when buffer is stalling
    - Upgrade when buffer has been healthy for a sustained period
    - Stay when buffer is filling or recently downgraded
    """

    def __init__(
        self,
        ladder: BitrateLadder | None = None,
        initial_bitrate: int | None = None,
        upgrade_cooldown_seconds: int = 10,
        downgrade_cooldown_seconds: int = 5,
    ) -> None:
        self.ladder = ladder or BitrateLadder()
        self.current_bitrate = initial_bitrate or self.ladder.lowest
        self.upgrade_cooldown_seconds = upgrade_cooldown_seconds
        self.downgrade_cooldown_seconds = downgrade_cooldown_seconds
        self._last_change_time = 0.0
        self._healthy_since: float | None = None
        self._downgrades = 0
        self._upgrades = 0

    @property
    def downgrade_count(self) -> int:
        """Number of downgrades performed."""
        return self._downgrades

    @property
    def upgrade_count(self) -> int:
        """Number of upgrades performed."""
        return self._upgrades

    def evaluate(self, buffer_state: BufferState, now: float | None = None) -> BitrateAction:
        """Evaluate the buffer state and return the recommended action.

        Args:
            buffer_state: Current buffer health state.
            now: Current time in seconds (for testing).

        Returns:
            The recommended bitrate action.
        """
        now = now if now is not None else time.time()
        cooldown_elapsed = now - self._last_change_time

        if buffer_state == BufferState.STALLING:
            # Downgrade if cooldown has elapsed
            if cooldown_elapsed >= self.downgrade_cooldown_seconds:
                self._healthy_since = None
                return BitrateAction.DOWNGRADE
            return BitrateAction.STAY

        if buffer_state == BufferState.HEALTHY:
            # Track how long we've been healthy
            if self._healthy_since is None:
                self._healthy_since = now
            elif (
                now - self._healthy_since >= self.upgrade_cooldown_seconds
                and cooldown_elapsed >= self.upgrade_cooldown_seconds
            ):
                return BitrateAction.UPGRADE
            return BitrateAction.STAY

        # FILLING or other states
        self._healthy_since = None
        return BitrateAction.STAY

    def apply(self, action: BitrateAction, now: float | None = None) -> int:
        """Apply an action and return the new bitrate.

        Args:
            action: The action to apply.
            now: Current time in seconds (for testing).

        Returns:
            The new bitrate in kbps.
        """
        now = now if now is not None else time.time()

        if action == BitrateAction.UPGRADE:
            new_bitrate = self.ladder.upgrade(self.current_bitrate)
            if new_bitrate != self.current_bitrate:
                self.current_bitrate = new_bitrate
                self._upgrades += 1
                self._last_change_time = now
                self._healthy_since = None
        elif action == BitrateAction.DOWNGRADE:
            new_bitrate = self.ladder.downgrade(self.current_bitrate)
            if new_bitrate != self.current_bitrate:
                self.current_bitrate = new_bitrate
                self._downgrades += 1
                self._last_change_time = now
                self._healthy_since = None

        return self.current_bitrate

    def reset(self) -> None:
        """Reset the controller to its initial state."""
        self.current_bitrate = self.ladder.lowest
        self._last_change_time = 0.0
        self._healthy_since = None
        self._downgrades = 0
        self._upgrades = 0