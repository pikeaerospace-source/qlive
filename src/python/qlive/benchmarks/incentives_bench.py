"""Tit-for-tat incentive benchmarks.

Measures the throughput of bandwidth accounting (record_sent/received)
and peer classification (get_contribution), the two hot paths in the
tit-for-tat incentive model.
"""

from __future__ import annotations

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.incentives import TitForTatManager


class IncentivesSuite(Suite):
    name = "incentives"
    description = "Tit-for-tat accounting and peer classification throughput."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        record_n = 400 if quick else 2000  # total record_sent/received operations
        peer_n = 200 if quick else 1000

        # 1. Bandwidth accounting throughput (record sent + received).
        def record_many() -> None:
            manager = TitForTatManager()
            for i in range(record_n // 2):
                manager.record_sent(f"peer-{i % 100}", 1000)
                manager.record_received(f"peer-{i % 100}", 900)

        record_s = best_time(record_many, repeat=3, number=1) / record_n
        results.append(
            Result("account.record", record_s * 1e6, "us", "per record_sent/received")
        )

        # 2. Classification throughput across peers.
        manager = TitForTatManager()
        for i in range(peer_n):
            manager.record_sent(f"peer-{i}", 1000)
            # Half the peers contribute, half are free-riders.
            manager.record_received(f"peer-{i}", 1000 if i % 2 == 0 else 100)

        def classify_all() -> None:
            for i in range(peer_n):
                manager.get_contribution(f"peer-{i}")

        classify_s = best_time(classify_all, repeat=3, number=1) / peer_n
        results.append(
            Result("account.classify", classify_s * 1e6, "us", "per get_contribution")
        )

        # 3. Free-rider detection throughput.
        def detect_free_riders() -> None:
            for i in range(peer_n):
                manager.check_free_rider(f"peer-{i}")

        detect_s = best_time(detect_free_riders, repeat=3, number=1) / peer_n
        results.append(
            Result(
                "account.free_rider_check", detect_s * 1e6, "us", "per check_free_rider"
            )
        )

        return results
