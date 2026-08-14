# QLive — TODO & Planning

Living document tracking outstanding tasks, open questions, design decisions, and the implementation roadmap for the QLive decentralized live-streaming protocol.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Phase 0 — Research & Specification

### Protocol Design
- [x] Write formal protocol specification document (`docs/protocol.md`)
- [x] Define the QDN signaling schema (stream metadata, peer lists, encryption keys)
- [x] Specify the ephemeral chunk format (CMAF/fMP4 container, sequence IDs, timestamps, hashes)
- [x] Design the cryptographic signing/verification scheme for in-flight chunks
- [x] Define the swarm membership protocol (join/leave/health-check)
- [x] Specify the tree-vs-mesh fallback handoff logic
- [x] Document the RAM sliding-window buffer semantics (size, eviction, retention policy)
- [x] Define the Live → VOD archival pipeline (chunk aggregation, QDN commit, Q-Tube manifest)

### Research Questions
- [ ] **Reticulum integration:** How can Reticulum network routing be leveraged for low-overhead peer discovery? Evaluate latency vs. WebRTC.
- [ ] **NAT traversal:** What's the best strategy for peers behind NATs (STUN/TURN, hole punching, Reticulum's transport)?
- [ ] **Chunk size tuning:** Benchmark optimal fragment duration (500ms vs 1s) for latency vs. overhead tradeoff.
- [ ] **Buffer sizing:** Determine ideal sliding-window size (30s vs 60s) balancing resilience vs. RAM usage.
- [ ] **QDN signaling frequency:** How often should swarm peer lists be refreshed on QDN without bloating the chain?
- [ ] **Encryption model:** Per-stream symmetric keys vs. per-viewer asymmetric keys? Key rotation strategy?
- [ ] **Qortal Core API surface:** What existing Qortal Core endpoints can be reused (QDN publish, name registration, peer discovery)?
- [ ] **Bandwidth measurement:** How to accurately measure peer bandwidth contribution for tit-for-tat and proof-of-relay?

---

## Phase 1 — Core Transport

### Ephemeral Chunking Engine
- [x] Implement CMAF/fMP4 segmenter (FFmpeg wrapper or native)
- [x] Implement chunk signing (Qortal Name/Key pair)
- [x] Implement chunk verification on viewer nodes
- [x] Implement chunk sequence tracking and gap detection
- [x] Implement retransmission request protocol for missing chunks

### RAM Sliding-Window Buffer
- [x] Implement in-memory ring buffer for live fragments
- [x] Implement eviction policy (oldest-first, window-based)
- [x] Implement buffer health monitoring (fill rate, stall detection)
- [x] Implement graceful degradation (adaptive bitrate on buffer pressure)

---

## Phase 2 — Swarm & Discovery

### Dual-Layer Peer Swarm
- [x] Implement primary delivery tree construction (capacity-based node selection)
- [x] Implement secondary local mesh (WebRTC/Reticulum data channels)
- [x] Implement tree → mesh fallback on parent drop
- [x] Implement mesh fragment exchange (missing-chunk pull)
- [x] Implement peer health monitoring and tree rebalancing
- [x] Implement swarm membership churn handling

### QDN Signaling Integration
- [x] Define and publish stream metadata schema to QDN
- [x] Implement swarm peer list publication/refresh
- [x] Implement encryption key distribution via QDN
- [x] Implement stream discovery (find active streams by Qortal Name)
- [x] Implement stream lifecycle states (announced, live, ended, archived)

---

## Phase 3 — VOD Bridge (Live → Q-Tube)

### Archival Pipeline
- [x] Implement background aggregation of expired live chunks
- [x] Implement QDN data chunk creation (10MB–50MB blocks)
- [x] Implement Q-Tube manifest generation
- [x] Implement automatic publish on stream end
- [x] Implement partial-archive recovery (stream interrupted mid-way)
- [x] Implement archive integrity verification (hash chain)

### Q-Tube Integration
- [ ] Coordinate with Q-Tube team on manifest format compatibility
- [ ] Implement "Watch Replay" link on live stream pages
- [ ] Implement live → VOD transition UX (no re-encoding)

---

## Phase 4 — Incentives & Reputation

### Tit-for-Tat Data Swapping
- [ ] Implement bandwidth contribution tracking per peer
- [ ] Implement prioritization logic (reward contributing peers)
- [ ] Implement free-rider detection and throttling

### Proof-of-Relay
- [ ] Design signed bandwidth receipt format
- [ ] Implement receipt generation on relay nodes
- [ ] Implement receipt verification on receiving nodes
- [ ] Explore integration with Qortal minting weight / node reputation
- [ ] Document incentive model economics

---

## Phase 5 — UX & Tooling

### Broadcaster App
- [ ] CLI tool for starting a broadcast (`qlive broadcast`)
- [ ] Web UI for stream management (start/stop, preview, stats)
- [ ] FFmpeg integration (RTMP/RTSP/device input)
- [ ] Stream health dashboard (viewer count, bandwidth, buffer status)

### Viewer App
- [ ] CLI tool for watching a stream (`qlive watch`)
- [ ] Web player (HLS/CMAF playback, low-latency mode)
- [ ] Stream discovery UI (browse active streams)
- [ ] Chat integration (optional, via QDN or separate channel)

### Q-Tube Integration
- [ ] Embed QLive player in Q-Tube
- [ ] "Live Now" section on Q-Tube
- [ ] Streamer profile integration (Qortal Name → live streams)

---

## Open Design Questions

These are unresolved questions that need discussion/decision:

1. **Transport layer:** WebRTC vs. Reticulum vs. both? WebRTC is battle-tested for media; Reticulum is Qortal-native but less proven for high-bandwidth video.
2. **Encryption:** Should streams be public (unencrypted, signed only) or private (encrypted, key-gated)? Support both?
3. **Adaptive bitrate:** Should QLive support multi-bitrate ladders (like HLS) or single-bitrate for v1? Multi-bitrate adds complexity but improves UX on poor connections.
4. **Archive ownership:** Who commits the VOD archive — the broadcaster only, or any node that has the full stream? (Fault tolerance vs. spam risk.)
5. **Proof-of-relay economics:** Should relay rewards be minting-weight-based, reputation-based, or purely social (tit-for-tat)? What prevents gaming?
6. **QDN signaling cadence:** How often to refresh swarm peer lists on QDN? Too frequent = chain bloat; too infrequent = stale peer lists.
7. **Stream persistence:** What happens if the broadcaster's node dies mid-stream? Graceful "stream ended" vs. swarm takeover?
8. **Multi-streamer support:** Can multiple broadcasters stream simultaneously on the same Qortal Name? (e.g., multi-camera events.)
9. **Latency target:** What's the acceptable end-to-end latency? Sub-1s (WebRTC-style) vs. 2–5s (low-latency HLS)? This drives the entire architecture.
10. **Mobile support:** Should v1 target desktop browsers only, or also mobile (iOS Safari has WebRTC/CMAF constraints)?

---

## Ideas & Future Enhancements

- [ ] **Simulcast / SVC:** Scalable Video Coding for bandwidth-adaptive delivery without multiple encodes.
- [ ] **Stream recording on demand:** Let viewers request a "record this stream" that archives to their own QDN space.
- [ ] **Multi-camera / multi-angle:** Publisher publishes multiple video tracks; viewers switch angles.
- [ ] **Live chat:** Decentralized chat channel tied to the stream (QDN-based or ephemeral mesh).
- [ ] **Donations / tipping:** QORT tipping integrated into the player (Qortal Name → QORT transfer).
- [ ] **Stream scheduling:** Announce upcoming streams via QDN (calendar/event metadata).
- [ ] **Analytics:** Privacy-preserving viewer/bandwidth analytics for streamers.
- [ ] **Relay marketplace:** Nodes advertise relay capacity; streamers "rent" relay nodes for guaranteed quality.
- [ ] **Offline-first playback:** Pre-fetch live stream to local cache for later VOD (viewer-initiated).
- [ ] **Qortal Name verification badge:** Verified streamers get a visual badge in the UI.

---

## Milestone Checklist

- [ ] **M0 — Spec freeze:** Protocol spec v1.0 approved
- [ ] **M1 — PoC:** Single broadcaster → single viewer over ephemeral mesh (no QDN yet)
- [ ] **M2 — Swarm:** 10+ viewers with tree+mesh fallback working
- [ ] **M3 — QDN signaling:** Stream discovery + peer lists via QDN
- [ ] **M4 — VOD bridge:** Live stream auto-archives to Q-Tube
- [ ] **M5 — Incentives:** Tit-for-tat + proof-of-relay live
- [ ] **M6 — Public beta:** Broadcaster + viewer apps usable by non-technical users
- [ ] **M7 — Production:** Q-Tube integration, mobile support, adaptive bitrate

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| — | — | — |

*(Append decisions here as they're made.)*

---

*This document is a living artifact. Update it as the project evolves.*