# CHUNK-SIZE-TUNING — Research

**Research task:** Benchmark optimal fragment duration (500ms vs 1s) for the latency vs. overhead tradeoff.

**Status:** In progress (`[~]`)

**Related:** [protocol.md](protocol.md) §3.4, [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Performance Tuning

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] What is the optimal fragment duration (500ms vs 1s vs 2s) for latency vs. overhead?
- [x] Quantify per-chunk fixed overhead (header + signature + hash).
- [x] Quantify per-chunk CPU cost (signing, verification, hashing).
- [ ] Measure end-to-end latency at different fragment durations (requires live transport harness).
- [ ] Measure the effect of fragment duration on FFmpeg keyframe/segment alignment.

---

## Findings

### 1. Fixed per-chunk overhead

The QLive chunk header is **155 bytes** fixed, regardless of payload size:

| Field | Size |
| --- | --- |
| Magic | 4 B |
| Version | 1 B |
| Stream ID | 32 B |
| Sequence ID | 8 B |
| Timestamp | 8 B |
| Duration | 2 B |
| Payload Size | 4 B |
| Payload Hash (SHA-256) | 32 B |
| Signature (Ed25519) | 64 B |
| **Total** | **155 B** |

### 2. Overhead ratio vs. fragment duration & bitrate

Measured overhead (155 B / payload size) across the supported fragment durations and typical bitrates:

| Bitrate | 500ms | 1000ms | 2000ms |
| --- | --- | --- | --- |
| 1000 kbps | 0.248% | 0.124% | 0.062% |
| 3000 kbps | 0.083% | 0.041% | 0.021% |
| 4500 kbps | 0.055% | 0.028% | 0.014% |
| 6000 kbps | 0.041% | 0.021% | 0.010% |

**Conclusion:** Even at the worst case (500ms fragments @ 1 Mbps), the fixed overhead is only **0.25%** of the payload. Bandwidth overhead is **not** a meaningful driver of fragment-duration choice. The real drivers are **latency** and **CPU cost per chunk**.

### 3. Chunk rate vs. fragment duration

| Duration | Chunks/s | Chunks/hour |
| --- | --- | --- |
| 500ms | 2.0 | 7,200 |
| 1000ms | 1.0 | 3,600 |
| 2000ms | 0.5 | 1,800 |

Shorter fragments double (or quadruple) the number of chunks that must be signed, hashed, verified, buffered, and tracked per unit time.

### 4. CPU cost per chunk (measured, real `chunk.py`)

Ed25519 sign/verify and SHA-256 hashing, measured on Python 3.12 (CPython, `cryptography` backend):

| Bitrate (1s chunk) | Payload | Sign | Verify | SHA-256 |
| --- | --- | --- | --- | --- |
| 1000 kbps | 125 KB | 388 µs | 281 µs | 71 µs |
| 4500 kbps | 562 KB | 1480 µs | 959 µs | 343 µs |
| 6000 kbps | 750 KB | 1986 µs | 1222 µs | 416 µs |

**Key finding as of the 2026-08-14 measurement:** signing the full payload
scaled with bitrate because `Chunk.signing_data` covered `header + payload`.
Per the [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md) decision, `chunk.py` now
signs **only the header** (which embeds the `payload_hash`), so Ed25519
sign/verify cost is **constant** (~50–100 µs) regardless of payload size; the
SHA-256 hash step above is the only residual per-byte cost. Re-run `chunk_bench`
against the updated implementation to re-measure.

- At 1s fragments, signing a 4.5 Mbps chunk costs ~1.5ms — ~0.15% of the 1s budget on the broadcaster. Negligible for a single stream.
- At 500ms fragments, chunk rate doubles, so per-second signing cost doubles (~0.3% at 4.5 Mbps). Still negligible for one stream, but it compounds on relay nodes that verify every chunk for every downstream peer.

---

## Analysis: Latency vs. Overhead

| Factor | 500ms | 1000ms | 2000ms |
| --- | --- | --- | --- |
| Glass-to-glass latency floor | ~0.5s | ~1.0s | ~2.0s |
| Fixed overhead ratio | highest | mid | lowest |
| Chunk/s (CPU, bookkeeping) | 2× | 1× | 0.5× |
| Resilience granularity (retransmit unit) | finer | mid | coarser |
| FFmpeg keyframe alignment | tighter | standard | looser |

- **Latency** is dominated by fragment duration + buffer depth + transport. 500ms fragments are the only way to approach sub-1s glass-to-glass latency.
- **CPU/overhead** is not a practical constraint at any supported duration (overhead < 0.25%, sign < 0.3% of budget).
- **Retransmission granularity:** smaller fragments mean a lost chunk loses less media, but generates more retransmit requests (more bookkeeping).

---

## Test Results

Benchmark harness: `/tmp/qlive_research_bench.py` (sections 1, 2, 6). Run against the installed `qlive` package (Python 3.12, `cryptography` 42+, `qlive` 0.1.0). Full test suite: **266 passed**.

Raw numbers reproduced in the tables above.

---

## Recommendation

1. **Keep `DEFAULT_FRAGMENT_MS = 1000`** as the default. It is the sweet spot: sub-2s latency is achievable, overhead is negligible, and CPU cost is trivial.
2. **Allow 500ms as an opt-in "low-latency" mode** for interactive streams (gaming, chat-driven content) where sub-1s latency matters. The 2× chunk-rate cost is acceptable.
3. **Use 2000ms only for archival-oriented or very-high-latency-tolerant streams**, or as an automatic fallback when a broadcaster's CPU is saturated.
4. **Fix signing to cover only the payload hash** (not the full payload) so sign/verify cost becomes constant (~50–100 µs) regardless of bitrate. This removes the only scaling cost that grows with fragment size and is a prerequisite for cheap 500ms operation at high bitrates.

---

## Open Questions

- [ ] What is the measured end-to-end latency of the full pipeline (segmenter → sign → tree → buffer → play) at each duration? Needs a live transport harness (TODO-RESEARCH.md → Benchmarking).
- [ ] Does FFmpeg's `-frag_duration` reliably produce aligned keyframes at 500ms, or does it round up to the GOP size? (The current segmenter uses `frag_keyframe`.)
- [ ] Should fragment duration be adaptive per-stream (broadcaster-driven) or fixed in the metadata?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Keep 1s default; 500ms opt-in for low-latency | Overhead < 0.25% at all durations; latency is the only real differentiator |
| 2026-08-14 | Recommend signing payload hash, not payload | Eliminates the only cost that scales with bitrate/fragment size |

---

*This document is a living artifact. Update it as benchmarks and the transport harness evolve.*
