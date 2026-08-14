"""RAM sliding-window buffer benchmarks.

Measures the memory footprint of the buffer at various bitrates and window
sizes, and the throughput of the add/evict path (the hot path every viewer
and relay runs once per chunk).
"""

from __future__ import annotations

import hashlib
import os
import time

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.buffer import SlidingWindowBuffer
from qlive.chunk import create_chunk

BITRATES_KBPS = (1000, 3000, 4500, 6000)
WINDOWS_SECONDS = (30, 45, 60)


class BufferSuite(Suite):
    name = "buffer"
    description = "RAM sliding-window buffer: memory usage and add/evict throughput."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        stream_id = hashlib.sha256(b"qlive-bench-buffer").digest()
        bitrates = (1000, 4500) if quick else BITRATES_KBPS
        windows = (30, 60) if quick else WINDOWS_SECONDS
        add_count = 500 if quick else 3000

        # 1. Measured memory usage at steady state (window + 1 transient chunk).
        for bitrate in bitrates:
            for window in windows:
                buffer = SlidingWindowBuffer(window_seconds=window)
                payload = os.urandom(int(bitrate * 1000 / 8))
                base_ts = int(time.time() * 1000)
                for seq in range(1, window + 2):  # +1 forces one eviction
                    buffer.add(
                        create_chunk(stream_id, seq, payload, timestamp=base_ts + seq * 1000)
                    )
                stats = buffer.stats
                results.append(
                    Result(
                        f"memory.{bitrate}kbps.{window}s",
                        stats.total_bytes / (1024 * 1024),
                        "MB",
                        f"{stats.total_chunks} chunks, state={stats.state.value}",
                    )
                )

        # 2. Add/evict throughput (steady-state: each add evicts one chunk).
        small_payload = os.urandom(1024)  # 1 KB chunks keep allocation noise low

        def add_many() -> None:
            buffer = SlidingWindowBuffer(window_seconds=30)
            base_ts = int(time.time() * 1000)
            for seq in range(1, add_count + 1):
                buffer.add(
                    create_chunk(stream_id, seq, small_payload, timestamp=base_ts + seq * 1000)
                )

        add_s = best_time(add_many, repeat=3, number=1) / add_count
        results.append(
            Result(
                "add.evict_steady",
                add_s * 1e6,
                "us",
                "per add with eviction (1KB chunks)",
            )
        )

        # 3. Lookup throughput (get + get_missing, the retransmit hot path).
        buffer = SlidingWindowBuffer(window_seconds=30)
        base_ts = int(time.time() * 1000)
        for seq in range(1, 61):
            buffer.add(create_chunk(stream_id, seq, small_payload, timestamp=base_ts + seq * 1000))

        def lookup() -> None:
            buffer.get(30)
            buffer.get_missing(1, 60)

        lookup_number = 200 if quick else 1000
        lookup_s = best_time(lookup, repeat=3, number=lookup_number)
        results.append(
            Result(
                "lookup.get_missing",
                lookup_s * 1e6,
                "us",
                "get + get_missing over 60 chunks",
            )
        )

        return results
