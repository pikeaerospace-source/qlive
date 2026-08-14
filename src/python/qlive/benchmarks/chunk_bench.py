"""Chunk format benchmarks.

Measures the fixed header overhead ratio and the CPU cost of the
cryptographic operations performed on every chunk: Ed25519 signing and
verification, SHA-256 payload hashing, and serialize/deserialize round-trips.
"""

from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.asymmetric import ed25519

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.chunk import HEADER_SIZE, Chunk, create_chunk

# Bitrates (kbps) and fragment durations (ms) to sweep.
BITRATES_KBPS = (1000, 3000, 4500, 6000)
DURATIONS_MS = (500, 1000, 2000)


class ChunkSuite(Suite):
    name = "chunk"
    description = "Chunk format overhead and crypto throughput (sign/verify/hash/serialize)."

    def run(self) -> list[Result]:
        results: list[Result] = []

        # 1. Fixed overhead ratio (deterministic — no timing needed).
        for bitrate in BITRATES_KBPS:
            for duration in DURATIONS_MS:
                payload = int(bitrate * 1000 / 8 * duration / 1000)  # bytes
                overhead_pct = HEADER_SIZE / payload * 100
                results.append(
                    Result(
                        f"overhead.{bitrate}kbps.{duration}ms",
                        overhead_pct,
                        "%",
                        f"header={HEADER_SIZE}B payload={payload}B",
                    )
                )

        # 2. Crypto throughput on 1-second chunks at each bitrate.
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        stream_id = hashlib.sha256(b"qlive-bench-stream").digest()

        for bitrate in BITRATES_KBPS:
            payload = os.urandom(int(bitrate * 1000 / 8))
            chunk = create_chunk(stream_id, 1, payload, duration=1000)

            sign_s = best_time(chunk.sign, private_key, repeat=3, number=50)
            verify_s = best_time(chunk.verify, public_key, repeat=3, number=50)
            hash_s = best_time(hashlib.sha256, payload, repeat=3, number=50)

            results.append(
                Result(f"sign.{bitrate}kbps", sign_s * 1e6, "us", "Ed25519 over header+payload")
            )
            results.append(
                Result(f"verify.{bitrate}kbps", verify_s * 1e6, "us", "Ed25519")
            )
            results.append(
                Result(f"sha256.{bitrate}kbps", hash_s * 1e6, "us", "payload hash only")
            )

        # 3. Serialize/deserialize round-trip throughput (1s @ 4.5 Mbps).
        payload = os.urandom(int(4500 * 1000 / 8))
        chunk = create_chunk(stream_id, 1, payload, duration=1000)
        chunk.sign(private_key)
        serialized = chunk.serialize()

        def roundtrip() -> None:
            data = chunk.serialize()
            Chunk.deserialize(data)

        roundtrip_s = best_time(roundtrip, repeat=3, number=100)
        results.append(
            Result("serialize", best_time(chunk.serialize, repeat=3, number=100) * 1e6, "us",
                   "header+signature+payload")
        )
        results.append(
            Result("roundtrip", roundtrip_s * 1e6, "us", f"serialize+deserialize {len(serialized)}B")
        )

        return results
