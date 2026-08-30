"""Relay reputation benchmarks.

Measures the throughput of ingesting confirmed bandwidth receipts into the
off-chain relay reputation tracker, and the cost of scoring/ordering relays
for routing priority / bounty ordering.
"""

from __future__ import annotations

import hashlib

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.proof import BandwidthReceipt, ReceiptState
from qlive.reputation import RelayReputationTracker


class ReputationSuite(Suite):
    name = "reputation"
    description = "Off-chain relay reputation: receipt ingestion and relay ordering."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        stream_id = hashlib.sha256(b"qlive-bench-reputation").digest()
        tracker = RelayReputationTracker(dispute_window_seconds=0)
        relay_count = 10 if quick else 100
        receipt_count = 50 if quick else 1000
        relays = [f"relay-{i}" for i in range(relay_count)]

        def make_receipt(relay: str, downstream: str, i: int) -> BandwidthReceipt:
            receipt = BandwidthReceipt(
                relay, downstream, stream_id, 1024 * 1024,
                start_sequence=i + 1, end_sequence=i + 1,
            )
            receipt.state = ReceiptState.REDEEMED
            return receipt

        receipts = [
            make_receipt(relays[i % relay_count], f"down-{i}", i)
            for i in range(receipt_count)
        ]

        def ingest() -> None:
            for receipt in receipts:
                tracker.consider_receipt(receipt, now_ms=0)

        ingest_s = best_time(ingest, repeat=3, number=5 if quick else 20)
        results.append(
            Result(
                "reputation.ingest",
                ingest_s / receipt_count * 1e6,
                "us",
                f"per receipt ({receipt_count} receipts)",
            )
        )

        order_s = best_time(
            lambda: tracker.order(list(relays), now_ms=0),
            repeat=3,
            number=200 if quick else 1000,
        )
        results.append(
            Result("reputation.order", order_s * 1e6, "us", f"{relay_count} relays")
        )

        return results