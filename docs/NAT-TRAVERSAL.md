# NAT-TRAVERSAL — Research

**Research task:** What's the best strategy for peers behind NATs (STUN/TURN, hole punching, Reticulum's transport)?

**Status:** In progress (`[~]`)

**Related:** [protocol.md](protocol.md) §11, [RETICULUM-INTEGRATION.md](RETICULUM-INTEGRATION.md), [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Transport Layer Research

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] What NAT traversal strategy for browser (WebRTC) peers?
- [~] What NAT traversal strategy for Qortal-native (non-browser) nodes?
- [~] Can Reticulum's transport replace STUN/TURN for Qortal nodes?
- [ ] Benchmark hole-punching success rates across NAT types (needs a real transport harness).
- [ ] Define a fallback chain when direct connectivity fails.

---

## Findings

### 1. WebRTC (browser peers)

WebRTC's ICE framework is the standard for browser NAT traversal:

- **STUN** — discovers the peer's public (mapped) address/port; enables **UDP hole punching** for most NAT types (full-cone, restricted-cone, port-restricted-cone).
- **TURN** — a relay server that forwards media when hole punching fails (symmetric NAT, or restrictive firewalls). TURN is a centralized fallback and costs bandwidth.
- **ICE** — orchestrates candidate gathering (host, server-reflexive via STUN, relayed via TURN) and connectivity checks.

**Limitations:** symmetric NAT (the hardest case) generally defeats UDP hole punching and requires TURN. Mobile carriers and some enterprise networks frequently impose symmetric NAT.

### 2. Reticulum (Qortal-native peers)

From the Reticulum documentation (`reticulum.network/manual/interfaces.html`):

- **AutoInterface** — LAN discovery over IPv6 link-local multicast + UDP (ports 29716/42671). Works without DHCP/routers on a shared L2 medium. No internet connectivity required.
- **TCPClientInterface / TCPServerInterface** — connect outbound to, or listen for, other Reticulum instances over TCP. This is the mechanism for traversing NAT via an outbound connection to a reachable peer.
- **I2PInterface** — tunnels traffic over the I2P anonymous network (NAT-oblivious).
- **Transport Nodes / announces** — Reticulum uses *announces* propagated through the network to build paths; a node behind NAT can reach the wider network by connecting outbound to a reachable peer/transport node, and its address becomes reachable via that path.

**Key property:** Reticulum has **no source addresses** and uses **ephemeral keys** with forward secrecy. Reachability is established via outbound connections + announce propagation rather than classic STUN-style reflexive address discovery.

### 3. Comparison

| Mechanism | NAT types handled | Centralized? | Notes |
| --- | --- | --- | --- |
| UDP hole punching (STUN) | full/restricted/port-restricted cone | No (STUN is just a lookup) | Fails on symmetric NAT |
| TURN relay | all | Yes | Bandwidth cost; last resort |
| Reticulum TCP client interface | all (outbound to reachable peer) | No (peer-to-peer) | Requires at least one reachable peer/transport node |
| Reticulum AutoInterface | LAN only | No | Zero-config LAN discovery |
| Reticulum I2P | all | No (I2P network) | High latency, low bandwidth |

---

## Analysis

- **Browser viewers** must use **WebRTC/ICE** (STUN + TURN fallback). There is no browser-native Reticulum stack, so WebRTC is the only viable data channel for browsers.
- **Qortal-native nodes** (CLI broadcaster/viewer, relays) can use **Reticulum** for connectivity, which sidesteps NAT entirely by establishing outbound TCP connections to reachable peers and routing via announces. This is more Qortal-native and avoids TURN's centralization.
- **Hybrid:** the swarm will contain both browser (WebRTC) and native (Reticulum) peers. A **gateway/relay** role is needed to bridge WebRTC data channels and Reticulum links.

---

## Recommendation

1. **Browser peers:** WebRTC ICE with STUN for reflexive discovery + UDP hole punching, and **TURN as a last-resort relay**. Accept TURN as a pragmatic centralized fallback for symmetric-NAT browsers (documented as a temporary relay, not a permanent dependency).
2. **Native Qortal peers:** use **Reticulum** (TCP client interface + announces) for connectivity; this handles NAT without STUN/TURN.
3. **Fallback chain (native):** AutoInterface (LAN) → direct outbound TCP → Reticulum transport-node path → (last resort) TURN-style relay.
4. **Fallback chain (browser):** host candidate → server-reflexive (STUN/hole punch) → TURN relay.
5. **Document symmetric-NAT handling** explicitly: symmetric NAT peers (browser) require TURN; native peers can use Reticulum's outbound-connect model.

---

## Open Questions

- [ ] What is the measured hole-punching success rate across real-world NAT types for the QLive swarm? (Needs a transport harness.)
- [ ] Who runs the STUN/TURN infrastructure? A Qortal-operated TURN pool vs. community relays?
- [ ] Can a Qortal node act as a TURN-equivalent relay for browser peers (bridging WebRTC ↔ Reticulum)?
- [ ] What is the connection-establishment latency of Reticulum TCP vs. WebRTC ICE (see RETICULUM-INTEGRATION.md)?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | WebRTC ICE (STUN+TURN) for browsers; Reticulum for native nodes | Browsers have no Reticulum stack; native nodes can avoid TURN centralization |
| 2026-08-14 | TURN as last-resort fallback only | Pragmatic for symmetric NAT; avoid as a permanent dependency |

---

*This document is a living artifact. Update it as traversal benchmarks and the transport harness evolve.*
