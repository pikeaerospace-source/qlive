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

- [ ] **Reticulum integration:** How can Reticulum network routing be leveraged for low-overhead peer discovery? Evaluate latency vs. WebRTC.
- [ ] **NAT traversal:** What's the best strategy for peers behind NATs (STUN/TURN, hole punching, Reticulum's transport)?
- [ ] **WebRTC vs. Reticulum:** Benchmark both for high-bandwidth video delivery
- [ ] **Transport fallback:** Design a fallback strategy if primary transport fails

### Research Notes
- [ ] Document Reticulum's architecture and capabilities
- [ ] Document WebRTC's data channel performance characteristics
- [ ] Compare connection establishment times
- [ ] Compare throughput under packet loss

---

## Performance Tuning

- [ ] **Chunk size tuning:** Benchmark optimal fragment duration (500ms vs 1s) for latency vs. overhead tradeoff.
- [ ] **Buffer sizing:** Determine ideal sliding-window size (30s vs 60s) balancing resilience vs. RAM usage.
- [ ] **Tree fanout:** Determine optimal tree fanout for different viewer counts
- [ ] **Mesh size:** Determine optimal mesh peer count for resilience
- [ ] **Retransmission timing:** Tune timeout and retry parameters

### Benchmarking
- [ ] Create benchmark harness for chunk delivery
- [ ] Measure end-to-end latency at different scales
- [ ] Measure bandwidth overhead of signing/verification
- [ ] Measure memory usage of sliding-window buffer
- [ ] Measure CPU usage of chunk processing

---

## QDN & Blockchain

- [ ] **QDN signaling frequency:** How often should swarm peer lists be refreshed on QDN without bloating the chain?
- [ ] **QDN chunk sizing:** Validate 10MB–50MB chunk size for QDN storage
- [ ] **Transaction costs:** Estimate QORT costs for stream registration and VOD archival
- [ ] **Chain bloat:** Analyze the impact of stream metadata on blockchain size

### Research Notes
- [ ] Document QDN storage limits and best practices
- [ ] Document QDN publish transaction costs
- [ ] Analyze QDN data retention policies

---

## Security Research

- [ ] **Encryption model:** Per-stream symmetric keys vs. per-viewer asymmetric keys? Key rotation strategy?
- [ ] **Key distribution:** Design secure key distribution for private streams
- [ ] **Sybil resistance:** Evaluate Qortal Name-based identity for sybil resistance
- [ ] **DoS resilience:** Design rate limiting and abuse prevention
- [ ] **Receipt forgery:** Evaluate proof-of-relay receipt forgery resistance

### Threat Modeling
- [ ] Document threat model for live streaming
- [ ] Analyze chunk injection attack vectors
- [ ] Analyze swarm manipulation attacks
- [ ] Analyze economic attacks on incentives

---

## Monetization Research

- [ ] **Proof-of-relay economics:** Should relay rewards be minting-weight-based, reputation-based, or purely social (tit-for-tat)? What prevents gaming?
- [ ] **QORT burn vs. transfer:** Evaluate deflationary vs. treasury models
- [ ] **Pay-Per-View pricing:** Research fair pricing models
- [ ] **Micro-tipping:** Evaluate state channel feasibility on Qortal
- [ ] **Revenue split:** Validate 80/15/5 split with community

### Economic Modeling
- [ ] Model relay node economics (bandwidth costs vs. rewards)
- [ ] Model streamer economics (production costs vs. revenue)
- [ ] Model viewer economics (willingness to pay)
- [ ] Simulate free-rider scenarios

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
| — | — | — | — |

---

*This document is a living artifact. Update it as research progresses.*