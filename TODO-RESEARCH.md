# QLive — Research & Open Questions TODO

Tracking research tasks, open design questions, and technical investigations for QLive.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Overview

This document tracks research items that need investigation before or during implementation. Each item should be expanded with findings, benchmarks, and recommendations as research progresses.

---

## Transport Layer Research

- [~] **Reticulum integration:** How can Reticulum network routing be leveraged for low-overhead peer discovery? Evaluate latency vs. WebRTC. → [docs/RETICULUM-INTEGRATION.md](docs/RETICULUM-INTEGRATION.md)
- [~] **NAT traversal:** What's the best strategy for peers behind NATs (STUN/TURN, hole punching, Reticulum's transport)? → [docs/NAT-TRAVERSAL.md](docs/NAT-TRAVERSAL.md)
- [ ] **WebRTC vs. Reticulum:** Benchmark both for high-bandwidth video delivery
- [ ] **Transport fallback:** Design a fallback strategy if primary transport fails

### Research Notes
- [ ] Document Reticulum's architecture and capabilities
- [ ] Document WebRTC's data channel performance characteristics
- [ ] Compare connection establishment times
- [ ] Compare throughput under packet loss

---

## Performance Tuning

- [~] **Chunk size tuning:** Benchmark optimal fragment duration (500ms vs 1s) for latency vs. overhead tradeoff. → [docs/CHUNK-SIZE-TUNING.md](docs/CHUNK-SIZE-TUNING.md)
- [~] **Buffer sizing:** Determine ideal sliding-window size (30s vs 60s) balancing resilience vs. RAM usage. → [docs/BUFFER-SIZING.md](docs/BUFFER-SIZING.md)
- [x] **Tree fanout:** Determine optimal tree fanout for different viewer counts → [docs/SWARM-SIMULATION.md](docs/SWARM-SIMULATION.md)
- [x] **Mesh size:** Determine optimal mesh peer count for resilience → [docs/SWARM-SIMULATION.md](docs/SWARM-SIMULATION.md)
- [x] **Retransmission timing:** Tune timeout and retry parameters → [docs/SWARM-SIMULATION.md](docs/SWARM-SIMULATION.md)

### Benchmarking
- [x] Create benchmark harness for chunk delivery → `src/python/qlive/benchmarks/`
- [~] Measure end-to-end latency at different scales (in-memory model done — `pipeline_bench.py`; real-network harness pending)
- [x] Measure bandwidth overhead of signing/verification → `chunk_bench.py`
- [x] Measure memory usage of sliding-window buffer → `buffer_bench.py`
- [x] Measure CPU usage of chunk processing → `chunk_bench.py`

---

## QDN & Blockchain

- [~] **QDN signaling frequency:** How often should swarm peer lists be refreshed on QDN without bloating the chain? → [docs/QDN-SIGNALING-FREQUENCY.md](docs/QDN-SIGNALING-FREQUENCY.md)
- [ ] **QDN chunk sizing:** Validate 10MB–50MB chunk size for QDN storage
- [ ] **Transaction costs:** Estimate QORT costs for stream registration and VOD archival
- [ ] **Chain bloat:** Analyze the impact of stream metadata on blockchain size

### Research Notes
- [ ] Document QDN storage limits and best practices
- [ ] Document QDN publish transaction costs
- [ ] Analyze QDN data retention policies

---

## Security Research

- [~] **Encryption model:** Per-stream symmetric keys vs. per-viewer asymmetric keys? Key rotation strategy? → [docs/ENCRYPTION-MODEL.md](docs/ENCRYPTION-MODEL.md)
- [x] **Key distribution:** Design secure key distribution for private streams → [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [x] **Sybil resistance:** Evaluate Qortal Name-based identity for sybil resistance → [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [x] **DoS resilience:** Design rate limiting and abuse prevention → [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [x] **Receipt forgery:** Evaluate proof-of-relay receipt forgery resistance → [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)

### Threat Modeling
- [x] Document threat model for live streaming → [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md)
- [x] Analyze chunk injection attack vectors → [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md)
- [x] Analyze swarm manipulation attacks → [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md)
- [x] Analyze economic attacks on incentives → [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md)

---

## Monetization Research

- [x] **Proof-of-relay economics:** Should relay rewards be minting-weight-based, reputation-based, or purely social (tit-for-tat)? What prevents gaming? → [docs/ECONOMIC-MODELING.md](docs/ECONOMIC-MODELING.md) §4
- [x] **QORT burn vs. transfer:** Evaluate deflationary vs. treasury models → [docs/MONETIZATION.md](docs/MONETIZATION.md) §5
- [x] **Pay-Per-View pricing:** Research fair pricing models → [docs/MONETIZATION.md](docs/MONETIZATION.md) §2
- [x] **Micro-tipping:** Evaluate state channel feasibility on Qortal → [docs/MONETIZATION.md](docs/MONETIZATION.md) §2
- [~] **Revenue split:** Validate 80/15/5 split with community → [docs/MONETIZATION.md](docs/MONETIZATION.md) §6 (documented; community validation pending)

### Economic Modeling
- [x] Model relay node economics (bandwidth costs vs. rewards) → [docs/ECONOMIC-MODELING.md](docs/ECONOMIC-MODELING.md) §1
- [x] Model streamer economics (production costs vs. revenue) → [docs/ECONOMIC-MODELING.md](docs/ECONOMIC-MODELING.md) §2
- [x] Model viewer economics (willingness to pay) → [docs/ECONOMIC-MODELING.md](docs/ECONOMIC-MODELING.md) §3
- [x] Simulate free-rider scenarios → [docs/ECONOMIC-MODELING.md](docs/ECONOMIC-MODELING.md) §5 + [docs/SWARM-SIMULATION.md](docs/SWARM-SIMULATION.md)

---

## UX Research

- [ ] **Latency target:** What's the acceptable end-to-end latency? Sub-1s (WebRTC-style) vs. 2–5s (low-latency HLS)? This drives the entire architecture.
- [ ] **Mobile support:** Should v1 target desktop browsers only, or also mobile (iOS Safari has WebRTC/CMAF constraints)?
- [ ] **Streamer onboarding:** What's the minimum setup for new streamers?
- [ ] **Viewer experience:** What features matter most to viewers?

### User Studies
- [ ] Interview potential streamers
- [ ] Interview potential viewers
- [ ] Test prototype with users
- [ ] Measure engagement metrics

---

## Open Design Questions

These are unresolved questions that need discussion/decision:

1. **Transport layer:** WebRTC vs. Reticulum vs. both?
2. **Encryption:** Should streams be public (unencrypted, signed only) or private (encrypted, key-gated)? Support both?
3. **Adaptive bitrate:** Should QLive support multi-bitrate ladders (like HLS) or single-bitrate for v1?
4. **Archive ownership:** Who commits the VOD archive — the broadcaster only, or any node that has the full stream?
5. **Proof-of-relay economics:** Should relay rewards be minting-weight-based, reputation-based, or purely social?
6. **QDN signaling cadence:** How often to refresh swarm peer lists on QDN?
7. **Stream persistence:** What happens if the broadcaster's node dies mid-stream?
8. **Multi-streamer support:** Can multiple broadcasters stream simultaneously on the same Qortal Name?
9. **Latency target:** Sub-1s vs. 2–5s?
10. **Mobile support:** Desktop only or also mobile?

---

## Research Log

| Date | Topic | Findings | Decision |
| --- | --- | --- | --- |
| 2026-08-14 | Chunk size | Overhead < 0.25% at all durations | 1s default; 500ms opt-in |
| 2026-08-14 | Buffer sizing | ≤ 43 MB at 6 Mbps/60s; window doesn't affect per-chunk recovery | 45s default (outage resilience) |
| 2026-08-14 | Encryption | AES-256-GCM ~800+ MB/s; full-payload signing scales with bitrate | Per-stream symmetric + hybrid envelopes; sign the hash |
| 2026-08-14 | Swarm tuning | Fanout 8 → depth 3 (~130 ms); mesh 4–8 → 97–100% recovery | Fanout 8, mesh 4–8, 1–2 retransmit attempts |
| 2026-08-14 | Security | Sybil is economic (name fee); relay cannot self-forge receipts | Two-tier incentives; bounded bounty pool |
| 2026-08-14 | Economics | 1 QORT/GB; free-riders only hurt >50% | Tit-for-tat + proof-of-relay; target worst free-riders |

---

*This document is a living artifact. Update it as research progresses.*