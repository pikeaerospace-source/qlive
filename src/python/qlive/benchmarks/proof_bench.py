"""Proof-of-relay benchmarks.

Measures the throughput of bandwidth receipt signing, verification, and the
full create → sign → verify → redeem lifecycle.
"""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.proof import BandwidthReceipt, ProofOfRelayManager


class ProofSuite(Suite):
    name = "proof"
    description = "Proof-of-relay: receipt sign/verify/redeem throughput."

    def run(self) -> list[Result]:
        results: list[Result] = []
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        stream_id = hashlib.sha256(b"qlive-bench-proof").digest()

        receipt = BandwidthReceipt("relay-1", "viewer-1", stream_id, 1024 * 1024)
        sign_s = best_time(receipt.sign, private_key, repeat=3, number=1000)
        verify_s = best_time(receipt.verify, public_key, repeat=3, number=1000)
        results.append(Result("receipt.sign", sign_s * 1e6, "us", "Ed25519"))
        results.append(Result("receipt.verify", verify_s * 1e6, "us", "Ed25519"))

        # Full redemption lifecycle (create → sign → verify → redeem).
        def redeem_cycle() -> float:
            manager = ProofOfRelayManager()
            r = manager.create_receipt("relay-1", "viewer-1", stream_id, 1024 * 1024)
            r.sign(private_key)
            manager.verify_receipt(r, public_key)
            r.timestamp = 0  # skip the 24h dispute window for benchmarking
            return manager.redeem(r)

        redeem_s = best_time(redeem_cycle, repeat=3, number=100)
        results.append(
            Result("receipt.redeem_cycle", redeem_s * 1e6, "us", "create+sign+verify+redeem")
        )

        return results
