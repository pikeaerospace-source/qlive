"""Retransmission protocol benchmarks.

Measures the throughput of request creation, chunk handling, timeout
detection, and full recovery cycles in the retransmission manager.
"""

from __future__ import annotations

import hashlib

from qlive.benchmarks.runner import Result, Suite, best_time
from qlive.chunk import create_chunk
from qlive.retransmit import RetransmissionManager

_CHUNK_PAYLOAD = b"\x00" * 1024


class RetransmitSuite(Suite):
    name = "retransmit"
    description = "Retransmission manager: request/handle/timeout/recovery throughput."

    def run(self, quick: bool = False) -> list[Result]:
        results: list[Result] = []
        stream_id = hashlib.sha256(b"qlive-bench-retransmit").digest()
        request_n = 200 if quick else 1000
        handle_number = 200 if quick else 1000
        timeout_n = 100 if quick else 500
        recovery_number = 20 if quick else 100

        # 1. Request creation throughput.
        def make_requests() -> None:
            manager = RetransmissionManager()
            for i in range(request_n):
                manager.request(stream_id, [i], f"peer-{i % 8}")

        request_s = best_time(make_requests, repeat=3, number=1) / request_n
        results.append(
            Result("request.create", request_s * 1e6, "us", "create retransmit request")
        )

        # 2. Chunk handling throughput (single pending request).
        manager = RetransmissionManager()
        request = manager.request(stream_id, [1, 2, 3], "peer-1")
        manager.mark_sent(request)
        chunk = create_chunk(stream_id, 1, _CHUNK_PAYLOAD, duration=1000)
        handle_s = best_time(
            manager.handle_chunk, chunk, "peer-1", repeat=3, number=handle_number
        )
        results.append(
            Result(
                "handle_chunk", handle_s * 1e6, "us", "incoming chunk → pending request"
            )
        )

        # 3. Timeout detection throughput (force-expire requests by back-dating).
        def check_timeouts() -> None:
            manager = RetransmissionManager()
            for i in range(timeout_n):
                req = manager.request(stream_id, [i], f"peer-{i % 8}")
                manager.mark_sent(req)
                req.created_at = 0  # force immediate expiry
            manager.check_timeouts()

        timeout_s = best_time(check_timeouts, repeat=3, number=1) / timeout_n
        results.append(
            Result("timeout.check", timeout_s * 1e6, "us", "per expired request")
        )

        # 4. Full recovery cycle (request → mark_sent → receive all → complete).
        def recovery_cycle() -> bool:
            manager = RetransmissionManager()
            req = manager.request(stream_id, [1, 2, 3], "peer-1")
            manager.mark_sent(req)
            for seq in (1, 2, 3):
                manager.handle_chunk(
                    create_chunk(stream_id, seq, _CHUNK_PAYLOAD, duration=1000),
                    "peer-1",
                )
            return req.is_complete

        recovery_s = best_time(recovery_cycle, repeat=3, number=recovery_number)
        results.append(
            Result(
                "recovery.cycle", recovery_s * 1e6, "us", "full 3-chunk recovery cycle"
            )
        )

        return results
