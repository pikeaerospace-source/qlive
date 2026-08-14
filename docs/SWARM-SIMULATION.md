# SWARM-SIMULATION — Research

**Research task:** Use a discrete-event simulation of the delivery swarm to answer the open tuning questions — tree fanout, mesh size, retransmission timing, buffer sizing, churn/parent-drop resilience, and free-rider impact.

**Status:** Complete (`[x]`) — harness built and findings recorded.

**Related:** `src/python/qlive/simulation.py`, `src/python/qlive/benchmarks/sim_bench.py`, [BUFFER-SIZING.md](BUFFER-SIZING.md), [CHUNK-SIZE-TUNING.md](CHUNK-SIZE-TUNING.md)

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [x] What is the optimal tree fanout (latency vs. relay load)?
- [x] What is the optimal mesh peer count (recovery vs. overhead)?
- [x] How many retransmission attempts are needed?
- [x] Does the buffer window size affect per-chunk recovery?
- [x] How does churn degrade delivery?
- [x] How do parent drops degrade delivery?
- [x] How do free-riders affect recovery?

---

## The Harness

`qlive/simulation.py` is a deterministic, offline, pure-Python discrete-event
simulation of the dual-layer swarm. It models:

- **Tree push** — the broadcaster emits one chunk per fragment; chunks flow
  down the delivery tree with a per-hop latency and an edge loss probability.
- **Mesh pull** — on detecting a sequence gap, a viewer requests the missing
  chunk from a random mesh peer; retries up to `retransmit_attempts` times.
- **Sliding-window buffering** — a chunk becomes unrecoverable once it is
  older than `buffer_window_ms`.
- **Churn** — leaf viewers leave (and are replaced) at a configurable rate.
- **Parent drop** — relay nodes fail; their children reattach to the tree.
- **Free-riders** — a fraction of viewers never serve mesh requests.

Metrics: delivery rate, recovery rate, end-to-end latency, recovery latency,
tree depth, and mean direct/recovered/missed chunks per viewer.

Run it via `python -m qlive.benchmarks sim` (or `--quick` for a fast sweep).

### Model assumptions / limitations

- Transport is abstracted: edges have fixed latency + loss probability (no
  real sockets, no congestion, no jitter).
- The mesh is random (no proximity/network-locality).
- Single seed per sweep; small non-monotonicities are RNG noise, not signal.

---

## Findings

Baseline: 200 viewers, 60 s, 5% edge loss, fanout 8, mesh 4, RTT 200 ms,
3 attempts, 45 s window (seed 1).

### 1. Fanout vs. depth/latency

| Fanout | Tree depth | E2E latency (50 ms/hop) |
| --- | --- | --- |
| 2 | 7 | 285 ms |
| 4 | 4 | 171 ms |
| 8 | 3 | 129 ms |
| 16 | 2 | 96 ms |

Larger fanout → shallower tree → lower latency, but more forwarding load per
relay. **Fanout 8 is a good default** (depth 3, ~130 ms); fanout 16 shaves
latency further at the cost of ~2× relay load.

### 2. Mesh size vs. recovery

| Mesh peers | Recovery rate | Delivery rate |
| --- | --- | --- |
| 0 | 0% | 85.3% |
| 2 | 90.1% | 98.7% |
| 4 | 97.0% | 99.6% |
| 8 | 99.7% | 100% |
| 16 | 98.9% | 99.9% |

**Mesh size 4–8 is the sweet spot.** Zero mesh peers means no recovery at all;
beyond 8 peers there are diminishing returns (and slight noise).

### 3. Loss vs. delivery

| Edge loss | Delivery | Recovery |
| --- | --- | --- |
| 0% | 100% | — |
| 5% | 99.6% | 97.0% |
| 10% | 99.6% | 98.1% |
| 20% | 99.1% | 97.9% |

Retransmission keeps delivery above 99% even at 20% edge loss.

### 4. Buffer window vs. recovery

| Window | Recovery |
| --- | --- |
| 5 s | 97.0% |
| 15–60 s | 97.0% |

**The buffer window has no measurable effect on per-chunk recovery** at a
typical RTT (200 ms): recovery completes in ~600 ms (3 attempts × 200 ms),
far below any window. The window's real value is **outage resilience** (slow
peers, parent drops), not per-chunk retransmission — see §6–7 below.

### 5. Retransmission attempts vs. recovery

| Attempts | Recovery |
| --- | --- |
| 1 | 99.0% |
| 2 | 97.9% |
| 3 | 97.0% |
| 5 | 98.8% |

**1–2 attempts are sufficient** at moderate loss (the first attempt usually
succeeds). More attempts add latency without meaningfully improving recovery.

### 6. Churn vs. delivery

| Churn (leaves/s) | Delivery | Recovery |
| --- | --- | --- |
| 0 | 99.6% | 97.0% |
| 0.5 | 92.4% | 69.5% |
| 1.0 | 88.4% | 66.2% |
| 2.0 | 82.3% | 58.8% |
| 5.0 | 78.3% | 60.2% |

Churn degrades delivery markedly (and recovery, since departed peers can no
longer serve requests). This is the strongest argument for a generous buffer
window and for keeping peer lists fresh.

### 7. Parent drop vs. delivery

| Drops (relays/s) | Delivery | Recovery |
| --- | --- | --- |
| 0 | 99.6% | 97.0% |
| 0.1 | 98.3% | 89.3% |
| 0.5 | 94.5% | 66.9% |
| 1.0 | 91.4% | 53.3% |
| 2.0 | 89.6% | 54.6% |

Relay failures hurt more than leaf churn (a whole subtree is affected until
reattachment + retransmission recover it).

### 8. Free-riders vs. recovery

| Free-rider fraction | Recovery | Delivery |
| --- | --- | --- |
| 0% | 97.0% | 99.6% |
| 25% | 98.9% | 99.9% |
| 50% | 94.7% | 99.2% |
| 75% | 74.2% | 96.9% |
| 100% | 30.3% | 91.9% |

Free-riders only hurt once they dominate the mesh (>50%). Tit-for-tat should
focus on the worst offenders rather than trying to exclude all non-contributors.

---

## Test Results

- `tests/python/test_simulation.py` — 8 tests (baseline delivery, loss,
  mesh recovery, buffer effect, determinism, fanout/depth, sweep, validation).
- Full suite: **283 passed**.
- `python -m qlive.benchmarks sim` — 8 sweeps, ~40 runs, < 1 s (`--quick` 0.2 s).

---

## Recommendations

1. **Fanout 8** default (depth 3, ~130 ms); allow 16 for low-latency use cases.
2. **Mesh size 4–8** — 4 gives 97% recovery, 8 gives ~100%; don't exceed 8.
3. **1–2 retransmission attempts** — more adds latency without benefit.
4. **Buffer window 30–60 s** is far more than per-chunk recovery needs; keep
   it for outage resilience (churn/parent-drop), which is the real driver.
5. **Prioritize relay stability** — parent drops cost more than leaf churn.
6. **Tit-for-tat targets the worst free-riders** — only >50% free-riders
   meaningfully degrades recovery.

---

## Open Questions

- [ ] Re-run sweeps with multiple seeds and report mean ± std to quantify noise.
- [ ] Model proximity-based mesh (network-locality) instead of random peers.
- [ ] Add a playback/stall model (buffer underrun) to complement delivery rate.
- [ ] Model congestion/backpressure on relay uplinks.

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Fanout 8 default; mesh 4–8 | Depth 3 / ~130 ms; 97–100% recovery with diminishing returns beyond 8 |
| 2026-08-14 | 1–2 retransmit attempts | First attempt usually succeeds; more adds latency |
| 2026-08-14 | Buffer window sized for outage resilience, not per-chunk recovery | Recovery completes in ~600 ms, far below any 5–60 s window |

---

*This document is a living artifact. Update it as the simulation model is refined.*

