# QLive — Design Decision Register

**Status:** Living — consolidates the open design questions tracked in
[TODO.md](../TODO.md) → Open Design Questions and
[TODO-RESEARCH.md](../TODO-RESEARCH.md), recording which are **decided**
(and by what evidence) and which remain **open** with a recommendation.

**Purpose:** give a single, citable place for the architectural decisions that
were previously scattered across per-topic research docs and the TODO decision
logs, and make the remaining open questions (and what would settle them)
explicit.

**Related:** [protocol.md](protocol.md) §11, [architecture.md](architecture.md),
and the per-topic research docs linked in each entry below.

---

## Status Legend

| Status | Meaning |
| --- | --- |
| **Decided** | Settled and reflected in the spec and/or code. |
| **Proposed** | A recommendation with rationale; awaiting maintainer confirmation before it is treated as decided. |
| **Open** | No recommendation yet — needs data, a running node, or a product call. |

---

## Summary

| # | Question | Status | Resolution |
| --- | --- | --- | --- |
| 1 | Transport: WebRTC vs. Reticulum vs. both? | **Decided** | WebRTC data plane; Reticulum control plane |
| 2 | Encryption: public vs. private, support both? | **Decided** | Support both; per-stream AES-256-GCM + hybrid envelopes for private |
| 3 | Adaptive bitrate: multi-bitrate ladder in v1? | **Decided** | Yes — rendition ladder + adaptive controller |
| 4 | Archive ownership: broadcaster only, or any node? | **Decided** | Broadcaster by default; any node with full history MAY commit |
| 5 | Proof-of-relay economics: minting / reputation / social? | **Decided** | Two-tier: tit-for-tat + proof-of-relay (bounded pool); off-chain reputation |
| 6 | QDN signaling cadence? | **Decided** | Delta-triggered, 30–60 s cap; metadata on state change |
| 7 | Stream persistence: broadcaster dies mid-stream? | **Proposed** | No swarm takeover in v1; surviving nodes finalize a partial archive |
| 8 | Multi-streamer: several broadcasters on one Qortal Name? | **Proposed** | Allowed (distinct `streamId`s), but one *primary* live stream per Name in v1 |
| 9 | Latency target: sub-1 s vs. 2–5 s? | **Proposed** | ~2–3 s baseline; opt-in low-latency (~1 s) mode |
| 10 | Mobile: desktop only or also mobile? | **Open** | v1 desktop-first; mobile best-effort (iOS Safari constraints) |

UX research items (streamer onboarding, viewer experience) are covered in
[§11](#11-ux-research) below.

---

## 1. Transport layer

**Question:** WebRTC vs. Reticulum vs. both?

**Status: Decided.** **WebRTC is the data plane; Reticulum is the control
plane.** Bulk video never traverses Reticulum in v1.

- Data plane: WebRTC data channels (browser peers) and direct sockets
  (native↔native), negotiated by Reticulum.
- Control plane: Reticulum announces/handshakes for peer discovery, membership,
  health checks, retransmit requests.
- Rationale: Reticulum is strong at discovery/NAT but is not designed for
  multi-Mbps media; WebRTC is the proven low-latency media transport.

**Evidence:** [RETICULUM-INTEGRATION.md](RETICULUM-INTEGRATION.md) → Recommendation
+ Decisions Log; [NAT-TRAVERSAL.md](NAT-TRAVERSAL.md) → Recommendation;
[TODO.md](../TODO.md) Notes & Decisions Log (`2026-08-14`).

**Follow-up:** prototype a Reticulum control channel and benchmark announce
propagation vs. WebRTC ICE establishment
([RETICULUM-INTEGRATION.md](RETICULUM-INTEGRATION.md) → Open Questions).

## 2. Encryption model

**Question:** Public (signed only) or private (key-gated)? Support both?

**Status: Decided.** **Support both:**

- **Public** — signed-only, no encryption.
- **Private** — per-stream **AES-256-GCM** key, distributed via QDN as a
  **hybrid envelope** (symmetric stream key wrapped per authorized viewer),
  rotated every 5–10 min; chunk headers stay plaintext for routing.
- Chunks sign the **payload hash only** (constant sign/verify cost).

**Evidence:** [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md) → Recommendation +
Decisions Log; [protocol.md](protocol.md) §8.2; `src/python/qlive/encryption.py`;
[TODO.md](../TODO.md) Notes & Decisions Log (`2026-08-14`).

## 3. Adaptive bitrate

**Question:** Multi-bitrate ladders in v1?

**Status: Decided — implemented.** The broadcast advertises a **rendition
ladder** and the viewer runs an **adaptive controller** driven by buffer health.

- Default ladder (kbps): `[1000, 2000, 3000, 4500, 6000]`, advertised via the
  signaling `renditions` field.
- The viewer's `AdaptiveBitrateController` raises/lowers rendition on buffer
  pressure (graceful degradation).

**Evidence:** `src/python/qlive/adaptive.py`, `broadcaster.py`, `signaling.py`
(§`renditions`), `viewer.py`; [signaling-schema.md](signaling-schema.md)
(`renditions`); `tests/python/test_adaptive.py`.

**Note:** the Web UI exposes the current quality *label* but rendition
*selection* UI is pending (see [TODO-WEB-UI.md](../TODO-WEB-UI.md)).

---

## 4. Archive ownership

**Question:** Who commits the VOD archive — the broadcaster only, or any node
with the full stream?

**Status: Decided (fault tolerance).** The **broadcaster commits by default**;
if the broadcaster disappears, **any node holding the full fragment history MAY
commit** the archive, marked **partial** if incomplete. Viewers can watch a
partial archive.

- Anti-spam is economic: a QDN publish costs QORT, and integrity is enforced by
  the manifest hash chain.
- The archive reuses the live fragments verbatim — no re-encode.

**Evidence:** [protocol.md](protocol.md) §7.2–§7.3; [vod-pipeline.md](vod-pipeline.md);
`src/python/qlive/archival.py` (`QTubeManifest`, `verify_integrity`).

**Open sub-question:** should arbitrary-node commits require more than the
publish fee (per-chunk broadcaster signatures are already required)? Tracked in
[TODO-RESEARCH.md](../TODO-RESEARCH.md).

## 5. Proof-of-relay economics

**Question:** Minting-weight-based, reputation-based, or purely social?

**Status: Decided.** **Two-tier incentives** plus an **off-chain reputation
layer**; on-chain minting integration is **deferred** until Qortal Core exposes
it.

- Viewers: tit-for-tat (bandwidth accounting; free-rider throttling).
- Relays: proof-of-relay — downstream-signed, range-checked bandwidth receipts
  redeemed against a **bounded bounty pool**.
- Reputation: off-chain, time-decayed, diversity-weighted, capped; drives local
  routing/bounty ordering. No chain writes.

**Evidence:** [ECONOMIC-MODELING.md](ECONOMIC-MODELING.md),
[MINTING-INTEGRATION.md](MINTING-INTEGRATION.md),
[incentives.md](incentives.md); `src/python/qlive/proof.py`, `incentives.py`,
`reputation.py`; [TODO.md](../TODO.md) Notes & Decisions Log.

## 6. QDN signaling cadence

**Question:** How often to refresh swarm peer lists on QDN without bloating the
chain?

**Status: Decided.** **Delta-triggered updates with a 30–60 s cap** (publish
only when membership changed); **stream metadata on state change only**; **key
rotation** (5–10 min) decoupled from peer-list cadence. The peer list is a
**discovery hint**, not authoritative.

- "Chain bloat" clarified: peer-list updates consume **QDN storage/bandwidth and
  small publish fees**, not ledger space (QDN data is off-chain).

**Evidence:** [QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md) →
Recommendation + Decisions Log; [protocol.md](protocol.md) §4.3.

---

## 7. Stream persistence (broadcaster failure)

**Question:** What happens if the broadcaster's node dies mid-stream — graceful
"stream ended" or swarm takeover?

**Status: Proposed.** **No swarm takeover for v1** — the stream ends.

- Viewers keep playing from the RAM sliding-window buffer until fragments
  expire (window TTL); then playback interrupts (the Web UI's `Player` already
  handles this with recovery + a Retry overlay).
- Archival falls back to any node with the full history (§4), producing a
  **partial** archive.
- Rationale: a seamless takeover requires a second signer trusted by viewers
  (swarm re-signing or a quorum scheme) — significant complexity with new trust
  assumptions; out of scope for v1.
- **What would settle it:** a decision on whether mid-stream takeover is a v1
  requirement; if so, a re-signing/quorum design is needed.

## 8. Multi-streamer support

**Question:** Can several broadcasters stream simultaneously on the same Qortal
Name (e.g. multi-camera events)?

**Status: Proposed.** **Allowed at the protocol level, curated at the UX level:**
each stream is a distinct QDN resource (`QLIVE_STREAM_<streamId>` under the
publisher's Name), so multiple concurrent streamIds can coexist under one Name.
For v1 the UI presents **one primary live stream per Name**.

- Multi-angle / multi-camera is a **v1.x** enhancement (publish several
  streamIds + a group manifest so viewers can switch angles).
- Rationale: identity and discovery ambiguity (which stream does a Name's page
  show?) is a product problem, not a protocol one; a single primary keeps the
  profile/watch UX unambiguous.

**Evidence:** [signaling-schema.md](signaling-schema.md)
(`QLIVE_STREAM_<streamId>`); `src/js/src/data/qapp.ts` (`QLIVE_STREAM_PREFIX`).

## 9. Latency target

**Question:** Sub-1 s (WebRTC-style) or 2–5 s (low-latency HLS)? Drives the
whole architecture.

**Status: Proposed.** **~2–3 s glass-to-glass baseline, with an opt-in
low-latency mode approaching ~1 s.**

- Baseline: 1 s fragments (default) → 2–3 s end-to-end, robust to jitter.
- Low-latency: 500 ms fragments + hls.js `lowLatencyMode` → ~1 s; 2× chunk rate
  accepted (overhead is a fraction of a percent).
- Rationale: 1 s fragments already give sub-second *fragment* delivery; the
  remaining latency is buffer depth + transport. A 2–3 s default trades a little
  latency for resilience on real networks, which matters more than the last
  second for most content. Interactive content opts into low-latency.
- **What would settle it:** a measured end-to-end latency figure from a live
  transport harness ([CHUNK-SIZE-TUNING.md](CHUNK-SIZE-TUNING.md) → Open Questions).

**Evidence:** [CHUNK-SIZE-TUNING.md](CHUNK-SIZE-TUNING.md) → Recommendation;
[protocol.md](protocol.md) §1.1 (design principles) & §10 (constants);
Web UI low-latency toggle (`src/js/src/components/Player.tsx`).

## 10. Mobile support

**Question:** Desktop browsers only, or also mobile?

**Status: Open.** **v1 is desktop-first; mobile is best-effort.**

- Constraints: iOS Safari lacks broad WebRTC data-channel support and imposes
  autoplay/CMAF restrictions; background playback is limited.
- Recommendation: ship desktop (Chrome/Firefox/Safari/Edge) as the supported v1
  target; treat mobile as best-effort (playback works where the browser supports
  it) and defer a dedicated mobile experience.
- **What would settle it:** a decision on whether mobile is a v1 launch
  requirement (which would pull WebRTC/mobile work into scope).

**Evidence:** [TODO-RESEARCH.md](../TODO-RESEARCH.md) → UX Research / Mobile;
[TODO-WEB-UI.md](../TODO-WEB-UI.md) → Testing (mobile testing pending).

---

## 11. UX Research

### Streamer onboarding — minimum setup

**Status: Proposed.** Minimal path: **Qortal Name + FFmpeg** and one action.

- Media in via FFmpeg (RTMP/RTSP/device) → QLive segmenter; start with
  `qlive broadcast --name <name> --source <input>` or the dashboard's **Start
  broadcast**.
- No account beyond the Qortal Name; no server, CDN, or ingest to provision.
- **Evidence:** [README.md](../README.md) → Getting Started (CLI);
  `src/python/qlive/cli.py`; `src/js/src/pages/DashboardPage.tsx`.

### Viewer experience — features that matter most

**Status: Proposed.** Priorities, in order:

1. Fast time-to-first-frame (join → playback).
2. Low latency + a visible latency/buffer indicator.
3. Graceful recovery from drops (auto-recover + Retry).
4. Replay after the stream ends (auto-archive, no re-encode).
5. Discovery that surfaces what's live now (Featured/Trending/Following).

- **Evidence:** Web UI — `Player` (playback states, buffer chip, low-latency
  toggle), `DiscoveryPage` (Featured/Trending/Following), `WatchPage` (replay).

### User studies

**Status: Open.** Streamer/viewer interviews, prototype testing, and engagement
metrics require **real participants** — not achievable offline. Tracked in
[TODO-RESEARCH.md](../TODO-RESEARCH.md) → UX Research → User Studies.

---

## Follow-ups (open items that would change a status)

| Ref | Needs | Blocks |
| --- | --- | --- |
| 1 | Reticulum control-channel prototype + benchmarks | native transport |
| 4 | Anti-spam policy for arbitrary-node commits | archive ownership hardening |
| 7 | Decision: is mid-stream takeover a v1 requirement? | persistence design |
| 8 | Decision: multi-angle in v1 or v1.x? | multi-streamer UX |
| 9 | Measured end-to-end latency (live harness) | confirming latency target |
| 10 | Decision: is mobile a v1 launch requirement? | mobile scope |
| 11 | User studies (participants) | onboarding / viewer-experience validation |

---

*This register is a living artifact. Mark a **Proposed** item **Decided** once
confirmed (and add the corresponding entry to [TODO.md](../TODO.md) → Notes &
Decisions Log).*
