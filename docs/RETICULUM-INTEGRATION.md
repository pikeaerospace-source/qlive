# RETICULUM-INTEGRATION — Research

**Research task:** How can Reticulum network routing be leveraged for low-overhead peer discovery? Evaluate latency vs. WebRTC.

**Status:** In progress (`[~]`)

**Related:** [NAT-TRAVERSAL.md](NAT-TRAVERSAL.md), [protocol.md](protocol.md) §11, [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Transport Layer Research, [TODO-QORTAL-CORE.md](../TODO-QORTAL-CORE.md) → Reticulum Research

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] Can Reticulum provide low-overhead peer discovery for the QLive swarm?
- [~] Is Reticulum suitable for the high-bandwidth *data* plane, or only the control/signaling plane?
- [~] How does Reticulum latency compare to WebRTC?
- [ ] Prototype a Reticulum-based swarm transport and benchmark it.
- [ ] Document a concrete Reticulum integration approach.

---

## Findings

### 1. Reticulum architecture (from `reticulum.network`)

- **No source addresses** — packets carry no origin information; addresses are self-sovereign and portable.
- **Ephemeral keys + forward secrecy** — all links are encrypted by default; unencrypted packets are dropped.
- **Announce-based routing** — destinations propagate *announces* through the network to build paths; newly generated addresses become globally reachable in seconds-to-minutes.
- **Interfaces** — AutoInterface (LAN), TCP client/server, I2P, LoRa, etc. (see NAT-TRAVERSAL.md).
- **Designed for** high-latency, low-bandwidth, adverse conditions (LoRa, mesh radio). The project's own framing emphasizes "very high latency and extremely low bandwidth" operation.

### 2. Suitability for video

Reticulum is optimized for **low-bandwidth, high-latency** links. High-bandwidth video (multi-Mbps) is **not** its design target:

- Its per-packet overhead and routing model are tuned for small messages over constrained links.
- There is no published evidence of Reticulum sustaining multi-Mbps continuous throughput comparable to WebRTC data channels over a direct socket.
- WebRTC data channels (SCTP over DTLS over UDP) are battle-tested for exactly this use case and deliver line-rate throughput with sub-second latency.

### 3. Where Reticulum fits well

- **Peer discovery / signaling:** Reticulum's announce + path-resolution model is a natural fit for discovering active stream peers and exchanging small control messages, without relying on a central directory.
- **Control channel:** join/leave, health-check, retransmit requests, key envelopes — all low-bandwidth.
- **NAT traversal for native nodes:** Reticulum's outbound-connect model sidesteps NAT (see NAT-TRAVERSAL.md).

---

## Analysis

| Concern | Reticulum | WebRTC |
| --- | --- | --- |
| High-bandwidth data plane | Unproven / not designed for it | Battle-tested, line-rate |
| Low-latency (< 1s) | Designed for high-latency tolerance | Sub-second by design |
| Peer discovery (control) | Strong (announces, self-sovereign addressing) | Requires external signaling (QDN) |
| NAT traversal | Native (outbound connect) | ICE/STUN/TURN |
| Browser support | None (no browser stack) | Native |
| Qortal-native fit | High (Qortal ecosystem) | Lower (external dep) |

---

## Recommendation

1. **Use Reticulum for the control/signaling plane** (peer discovery, swarm membership, health checks, retransmit requests) for Qortal-native nodes. This is where Reticulum's announce-based routing and NAT-oblivious connectivity shine.
2. **Use WebRTC data channels for the high-bandwidth data plane**, especially for browser viewers. WebRTC is the proven choice for multi-Mbps, low-latency media.
3. **Do NOT route bulk video over Reticulum** in v1 — its low-bandwidth/high-latency design makes it a poor fit for the data plane. Revisit only if benchmarks show acceptable throughput.
4. **For native-to-native data**, evaluate a direct socket (TCP/UDP) transport as an alternative to WebRTC; Reticulum can negotiate the connection, then bulk data flows over the direct link.
5. **Prototype** (TODO-QORTAL-CORE.md → Reticulum Research): build a minimal Reticulum control channel and measure announce propagation latency and path-establishment time before committing.

---

## Open Questions

- [ ] What is the measured announce-propagation latency on a real Qortal/Reticulum network?
- [ ] Can Reticulum's TCP interface sustain even 1 Mbps continuously? (Benchmark required.)
- [ ] How do Reticulum addresses map to QLive swarm peer IDs?
- [ ] Is there a Reticulum↔WebRTC gateway pattern for mixed swarms?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Reticulum for control plane; WebRTC for data plane | Reticulum is strong at discovery/NAT but not designed for high-bandwidth video |
| 2026-08-14 | Defer Reticulum data-plane to post-benchmark | No evidence it sustains multi-Mbps throughput |

---

*This document is a living artifact. Update it as the Reticulum prototype and benchmarks progress.*
