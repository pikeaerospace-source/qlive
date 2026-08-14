"""Discrete-event simulation benchmarks.

Runs the swarm simulation (:mod:`qlive.simulation`) across design-parameter
sweeps to answer the open research questions: tree fanout, mesh size,
retransmission timing, buffer sizing, churn and parent-drop resilience, and
free-rider impact.
"""

from __future__ import annotations

from qlive.benchmarks.runner import Result, Suite
from qlive.simulation import SimConfig, run_sweep


def _base(quick: bool) -> SimConfig:
    return SimConfig(
        num_viewers=50 if quick else 200,
        duration_ms=15_000 if quick else 60_000,
        loss_rate=0.05,
        seed=1,
    )


class SimSuite(Suite):
    name = "sim"
    description = "Discrete-event swarm simulation: fanout, mesh, retransmit, buffer, churn, free-riders."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        base = _base(quick)

        # 1. Loss rate vs delivery/recovery.
        for value, r in run_sweep(base, "loss_rate", [0.0, 0.01, 0.05, 0.1, 0.2]):
            results.append(
                Result(
                    f"loss.{value}.delivery",
                    r.delivery_rate,
                    "",
                    f"recovery={r.recovery_rate:.3f}",
                )
            )

        # 2. Fanout vs tree depth / latency.
        for value, r in run_sweep(base, "fanout", [2, 4, 8, 16]):
            results.append(
                Result(
                    f"fanout.{value}.depth",
                    float(r.tree_depth),
                    "hops",
                    f"e2e={r.e2e_latency_ms:.0f}ms",
                )
            )

        # 3. Mesh size vs recovery.
        for value, r in run_sweep(base, "mesh_size", [0, 2, 4, 8, 16]):
            results.append(
                Result(
                    f"mesh.{value}.recovery",
                    r.recovery_rate,
                    "",
                    f"delivery={r.delivery_rate:.3f}",
                )
            )

        # 4. Buffer window vs recovery.
        for value, r in run_sweep(
            base, "buffer_window_ms", [5_000, 15_000, 30_000, 45_000, 60_000]
        ):
            results.append(
                Result(
                    f"buffer.{value // 1000}s.recovery",
                    r.recovery_rate,
                    "",
                    f"delivery={r.delivery_rate:.3f}",
                )
            )

        # 5. Retransmit attempts vs recovery.
        for value, r in run_sweep(base, "retransmit_attempts", [1, 2, 3, 5]):
            results.append(
                Result(
                    f"retransmit.{value}.recovery",
                    r.recovery_rate,
                    "",
                    f"delivery={r.delivery_rate:.3f}",
                )
            )

        # 6. Churn vs delivery.
        for value, r in run_sweep(base, "churn_per_second", [0.0, 0.5, 1.0, 2.0, 5.0]):
            results.append(
                Result(
                    f"churn.{value}.delivery",
                    r.delivery_rate,
                    "",
                    f"recovery={r.recovery_rate:.3f}",
                )
            )

        # 7. Parent drop vs delivery.
        for value, r in run_sweep(
            base, "parent_drop_per_second", [0.0, 0.1, 0.5, 1.0, 2.0]
        ):
            results.append(
                Result(
                    f"parentdrop.{value}.delivery",
                    r.delivery_rate,
                    "",
                    f"recovery={r.recovery_rate:.3f}",
                )
            )

        # 8. Free-rider fraction vs recovery.
        for value, r in run_sweep(
            base, "free_rider_fraction", [0.0, 0.25, 0.5, 0.75, 1.0]
        ):
            results.append(
                Result(
                    f"freerider.{value}.recovery",
                    r.recovery_rate,
                    "",
                    f"delivery={r.delivery_rate:.3f}",
                )
            )

        return results
