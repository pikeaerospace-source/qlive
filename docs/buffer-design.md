# RAM Sliding-Window Buffer

**Status:** Reference — mirrors `qlive/buffer.py` and `protocol.md` §6.

Live fragments are held strictly in RAM and evicted oldest-first, so nodes
leave **zero long-term disk footprint**.

---

## Parameters

| Parameter | Value |
| --- | --- |
| Default window | 45 s |
| Window range | 30–60 s |
| Memory ceiling | 256 MB |

## States

`filling` (fill < 80%) → `healthy` (≥ 80%) → `stalling` (< 30%) → `overflow`.

## Semantics

- Chunks are keyed by sequence ID and evicted once older than the window.
- Out-of-order insertion raises a gap; gaps are tracked for retransmission.
- Exceeding the memory ceiling raises `BufferFullError`.

---

## Sizing (from BUFFER-SIZING.md and SWARM-SIMULATION.md)

- RAM is negligible: ≤ 43 MB at 6 Mbps / 60 s.
- The window does **not** affect per-chunk retransmission recovery (which
  completes in ~600 ms); its real value is **outage resilience** (churn,
  parent drops).

---

## Implementation

- `qlive/buffer.py` — `SlidingWindowBuffer`, `BufferStats`, `BufferState`.

*See [protocol.md](protocol.md) §6 for the full specification.*
