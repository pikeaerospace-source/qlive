# QLive — TODO & Planning

Living document tracking outstanding tasks, open questions, design decisions, and the implementation roadmap for the QLive decentralized live-streaming protocol.

---

## Sub-TODO Documents

External dependency areas have their own dedicated TODO documents:

| Document | Focus |
| --- | --- |
| [TODO-QTUBE.md](TODO-QTUBE.md) | Q-Tube integration (live player, VOD replay, profiles) |
| [TODO-QORTAL-CORE.md](TODO-QORTAL-CORE.md) | Qortal Core integration (QDN, identity, minting) |
| [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md) | qapp-core submodule (Qortal UI lib: auth, QDN CRUD, player, state) |
| [TODO-WEB-UI.md](TODO-WEB-UI.md) | Web UI & frontend (dashboard, player, discovery) |
| [TODO-RESEARCH.md](TODO-RESEARCH.md) | Research & open design questions |

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
- [~] **Reticulum integration:** How can Reticulum network routing be leveraged for low-overhead peer discovery? Evaluate latency vs. WebRTC. → [docs/RETICULUM-INTEGRATION.md](docs/RETICULUM-INTEGRATION.md)
- [~] **NAT traversal:** What's the best strategy for peers behind NATs (STUN/TURN, hole punching, Reticulum's transport)? → [docs/NAT-TRAVERSAL.md](docs/NAT-TRAVERSAL.md)
- [~] **Chunk size tuning:** Benchmark optimal fragment duration (500ms vs 1s) for latency vs. overhead tradeoff. → [docs/CHUNK-SIZE-TUNING.md](docs/CHUNK-SIZE-TUNING.md)
- [~] **Buffer sizing:** Determine ideal sliding-window size (30s vs 60s) balancing resilience vs. RAM usage. → [docs/BUFFER-SIZING.md](docs/BUFFER-SIZING.md)
- [~] **QDN signaling frequency:** How often should swarm peer lists be refreshed on QDN without bloating the chain? → [docs/QDN-SIGNALING-FREQUENCY.md](docs/QDN-SIGNALING-FREQUENCY.md)
- [~] **Encryption model:** Per-stream symmetric keys vs. per-viewer asymmetric keys? Key rotation strategy? → [docs/ENCRYPTION-MODEL.md](docs/ENCRYPTION-MODEL.md)
- [~] **Qortal Core API surface:** What existing Qortal Core endpoints can be reused (QDN publish, name registration, peer discovery)? → [docs/QORTAL-CORE-API.md](docs/QORTAL-CORE-API.md)
- [~] **Bandwidth measurement:** How to accurately measure peer bandwidth contribution for tit-for-tat and proof-of-relay? → [docs/BANDWIDTH-MEASUREMENT.md](docs/BANDWIDTH-MEASUREMENT.md)

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
- [x] Implement "Watch Replay" link on live stream pages — Web UI `StreamCard`/`WatchPage` + `src/js/src/data/archive.ts` → [TODO-QTUBE.md](TODO-QTUBE.md)
- [x] Implement live → VOD transition UX (no re-encoding) — archive metadata drives `archiving → ready`/`partial`; the player plays the archived fragments unchanged → [docs/vod-pipeline.md](docs/vod-pipeline.md) §Viewer Replay UX

---

## Phase 4 — Incentives & Reputation

### Tit-for-Tat Data Swapping
- [x] Implement bandwidth contribution tracking per peer
- [x] Implement prioritization logic (reward contributing peers)
- [x] Implement free-rider detection and throttling

### Proof-of-Relay
- [x] Design signed bandwidth receipt format
- [x] Implement receipt generation on relay nodes
- [x] Implement receipt verification on receiving nodes
- [x] Implement off-chain relay reputation tracker (time decay, diversity weighting, capped contribution) → `qlive/reputation.py` (step 1 of [docs/MINTING-INTEGRATION.md](docs/MINTING-INTEGRATION.md) §Recommendation)
- [x] Explore integration with Qortal minting weight / node reputation → [docs/MINTING-INTEGRATION.md](docs/MINTING-INTEGRATION.md) (phased: off-chain relay reputation now; minting feed deferred to Qortal Core)
- [x] Document incentive model economics

---

## Phase 5 — UX & Tooling

### Broadcaster App
- [x] CLI tool for starting a broadcast (`qlive broadcast`)
- [x] Web UI for stream management (start/stop, preview, stats)
- [x] Publish stream metadata on start/stop (Web UI `selectPublisher()` seam → QDN `PUBLISH_QDN_RESOURCE`, offline in-memory registry)
- [x] FFmpeg integration (RTMP/RTSP/device input)
- [x] Stream health dashboard (viewer count, bandwidth, buffer status)

### Viewer App
- [x] CLI tool for watching a stream (`qlive watch`)
- [~] Web player (HLS/CMAF playback, low-latency mode) — adopt `qapp-core` VideoPlayer → [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md)
- [x] Stream discovery UI (browse active streams)
- [x] Chat integration (optional, via QDN or separate channel) — Web UI `ChatPanel` + offline chat seam (`src/js/src/data/chat.ts`); a mesh/WebSocket client replaces the simulator when the live transport lands → [TODO-WEB-UI.md](TODO-WEB-UI.md)

### Q-Tube Integration
- [ ] Embed QLive player in Q-Tube
- [ ] "Live Now" section on Q-Tube
- [ ] Streamer profile integration (Qortal Name → live streams)

---

## Open Design Questions

These are consolidated — with status, rationale, and evidence — in
[docs/DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md). Summary:

- **Decided** (in the spec and/or code): transport (§1), encryption (§2),
  adaptive bitrate (§3), archive ownership (§4), proof-of-relay economics (§5),
  QDN signaling cadence (§6).
- **Proposed** (recommendation, pending confirmation): stream persistence (§7),
  multi-streamer support (§8), latency target (§9).
- **Open:** mobile support (§10); streamer/viewer user studies.

Confirm a **Proposed** item to mark it Decided. The register's Follow-ups table
lists what each open/proposed item needs.

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
- [x] **Qortal Name verification badge:** Verified streamers get a visual badge in the UI.

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
| 2026-08-14 | 1s default fragment duration; 500ms opt-in | Overhead < 0.25% at all durations; latency is the only real differentiator |
| 2026-08-14 | 45s default buffer window (30–60s tunable) | RAM is negligible (< 43 MB max); resilience headroom is the driver |
| 2026-08-14 | Per-stream symmetric AES-256-GCM + hybrid key envelopes | Preserves multicast efficiency; enables per-viewer authorization |
| 2026-08-14 | Sign payload hash, not full payload | Makes sign/verify cost constant regardless of bitrate |
| 2026-08-14 | WebRTC for data plane; Reticulum for control plane | WebRTC is proven for high-bandwidth video; Reticulum is strong at discovery/NAT |
| 2026-08-14 | React + Vite for the Web UI | Qortal Q-App standard; largest ecosystem; best media-player libs |
| 2026-08-14 | Fanout 8; mesh 4–8; 1–2 retransmit attempts | Simulation: depth 3 / ~130 ms; 97–100% recovery with diminishing returns beyond 8 |
| 2026-08-14 | Two-tier incentives (tit-for-tat + proof-of-relay) | Tit-for-tat deters viewers; only proof-of-relay rewards relays economically |
| 2026-08-14 | Per-stream AES-256-GCM encryption implemented | Matches the encryption model; enables private streams |
| 2026-08-26 | Add `qapp-core` as a vendored git submodule (`qapp-core/`) | Reuse Qortal's tested React foundation (auth, QDN CRUD, player, state) and expose `qortalRequest` for real Qortal integration. Tracks in [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md) |
| 2026-10-12 | Consolidate the open design questions into [docs/DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md) | The 10 open questions were spread across per-topic research docs and this log, with several already decided. The register states each question's status (Decided/Proposed/Open), rationale, and evidence, and lists follow-ups. Open Design Questions here now point to it |

---

*This document is a living artifact. Update it as the project evolves.*