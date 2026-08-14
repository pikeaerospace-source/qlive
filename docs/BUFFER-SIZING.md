# BUFFER-SIZING — Research

**Research task:** Determine the ideal sliding-window size (30s vs 60s) balancing resilience vs. RAM usage.

**Status:** In progress (`[~]`)

**Related:** [protocol.md](protocol.md) §6, `src/python/qlive/buffer.py`, [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Performance Tuning

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] What is the ideal sliding-window size (30s vs 45s vs 60s)?
- [x] Quantify RAM usage vs. window size and bitrate.
- [x] Validate the buffer's memory accounting against real chunks.
- [ ] Measure resilience (stall recovery) as a function of window size under churn/packet loss.
- [ ] Determine the interaction between window size and retransmission timeout.

---

## Findings

### 1. Theoretical RAM usage

`RAM = bitrate × window`. For the supported window range (30–60s) and typical bitrates:

| Bitrate | 30s | 45s | 60s |
| --- | --- | --- | --- |
| 1000 kbps | 3.6 MB | 5.4 MB | 7.2 MB |
| 3000 kbps | 10.7 MB | 16.1 MB | 21.5 MB |
| 4500 kbps | 16.1 MB | 24.1 MB | 32.2 MB |
| 6000 kbps | 21.5 MB | 32.2 MB | 42.9 MB |

### 2. Measured RAM usage (real `SlidingWindowBuffer`)

Using the actual buffer implementation with synthetic 1s chunks (each sized to the bitrate):

| Bitrate | Window | Chunks held | Measured bytes | State |
| --- | --- | --- | --- | --- |
| 1000 kbps | 30s | 31 | 3.88 MB | healthy |
| 1000 kbps | 60s | 61 | 7.62 MB | healthy |
| 4500 kbps | 30s | 31 | 17.44 MB | healthy |
| 4500 kbps | 60s | 61 | 34.31 MB | healthy |

The buffer holds `window + 1` chunks transiently (the newest chunk is added before the oldest is evicted), which accounts for the slight overshoot above the theoretical value.

### 3. Memory ceiling

The current default `DEFAULT_MAX_MEMORY_BYTES = 256 MB` is generous: even a 6 Mbps stream at a 60s window uses only ~43 MB. The memory ceiling is effectively never the binding constraint for a single stream; it exists to protect against pathological cases (e.g., a peer flooding the buffer with oversized chunks).

---

## Analysis: Resilience vs. RAM

| Factor | 30s | 45s | 60s |
| --- | --- | --- | --- |
| RAM (6 Mbps) | 21.5 MB | 32.2 MB | 42.9 MB |
| Stall recovery headroom | least | mid | most |
| Retransmit window | 30s | 45s | 60s |
| Mesh fallback coverage | least | mid | most |
| Eviction pressure | highest | mid | lowest |

- **Resilience:** a larger window gives more time to recover a missing chunk from the mesh before it is evicted. This directly bounds how long a viewer can tolerate a stalled parent before the missing data is unrecoverable.
- **RAM:** even at the maximum (60s @ 6 Mbps), usage is ~43 MB — trivial on any modern node. RAM is **not** a practical constraint.
- **Latency:** a larger window does not directly add playback latency (playback is driven by the newest chunk), but a larger *target* buffer can mask network degradation for longer before the viewer notices.

---

## Test Results

Benchmark harness: `/tmp/qlive_research_bench.py` (sections 3, 4). Full test suite: **266 passed** (including `test_buffer.py`).

The buffer correctly:
- evicts oldest-first,
- enforces the 30–60s window bounds (raises `BufferError` outside the range),
- reports `healthy`/`filling`/`stalling` states based on fill ratio,
- enforces the memory ceiling (`BufferFullError`).

---

## Recommendation

1. **Keep `DEFAULT_BUFFER_SECONDS = 45`** as the default. It is the midpoint of the supported range and offers good resilience headroom at negligible RAM cost.
2. **Expose 30–60s as a tunable range** (already implemented and enforced in `buffer.py`). Lower-end (30s) for memory-constrained/embedded nodes; upper-end (60s) for high-churn networks.
3. **Tie the window to the retransmit timeout:** the window must be ≥ the worst-case retransmit round-trip + mesh fallback time, otherwise missing chunks are evicted before recovery completes. A 45s window comfortably covers the current 2s retransmit timeout × 3 attempts.
4. **Keep the 256 MB memory ceiling** as a safety valve, but document that it is not the binding constraint for normal operation.

---

## Open Questions

- [ ] Measure stall-recovery success rate vs. window size under simulated packet loss (needs a transport harness).
- [ ] Should the window size adapt dynamically based on observed churn/loss (e.g., widen on high churn, shrink on stable)?
- [ ] How does the window interact with the archival pipeline (chunks must be captured *before* eviction for VOD aggregation)?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Keep 45s default; 30–60s tunable | RAM is negligible (< 43 MB at max); resilience headroom is the real driver |
| 2026-08-14 | Window must exceed worst-case retransmit time | Prevents eviction of recoverable chunks |

---

*This document is a living artifact. Update it as resilience benchmarks and the transport harness evolve.*
