# QLive — Qortal Core Integration TODO

Tracking tasks for integrating QLive with Qortal Core for blockchain, QDN, and network infrastructure.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Overview

Qortal Core provides the underlying infrastructure QLive depends on:
1. **QDN** — Decentralized storage for stream metadata and VOD archives
2. **Identity** — Qortal Names for streamer authentication and chunk signing
3. **Peer network** — Node discovery and connectivity for the swarm
4. **Minting** — Potential integration for proof-of-relay rewards

> **Frontend shortcut:** The Web UI consumes Qortal Core through the **`qapp-core`**
> submodule (`qapp-core/`), which already implements Qortal auth (`useAuth`), QDN
> publish/fetch (`usePublish`, `useResources`), and the typed `qortalRequest` API
> bridge. Prefer reusing it over building a bespoke client — see
> [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md). The items below describe the underlying
> capability work regardless of consumer.

---

## QDN Integration

- [ ] Implement QDN publish for stream metadata documents
- [ ] Implement QDN publish for VOD archive chunks
- [ ] Implement QDN retrieval for stream discovery
- [ ] Implement QDN retrieval for VOD playback
- [ ] Handle QDN resource lifecycle (create, update, delete)
- [ ] Implement QDN data chunk size limits (10MB–50MB)
- [ ] Test QDN publish/retrieve roundtrip

### QDN API Surface
- [ ] Document QDN REST API endpoints used
- [ ] Document QDN WebSocket events for real-time updates
- [ ] Map QLive metadata schema to QDN resource types
- [ ] Define QDN resource naming convention for streams

---

## Identity & Signing

- [ ] Implement Qortal Name resolution to public keys
- [ ] Implement chunk signing with Qortal Name key pairs
- [ ] Implement chunk verification using resolved public keys
- [ ] Handle key rotation and revocation
- [ ] Implement streamer identity verification (name ownership proof)

### Key Management
- [ ] Document key storage best practices
- [ ] Implement secure key loading from Qortal Core
- [ ] Handle key backup and recovery
- [ ] Test cross-node key verification

---

## Peer Network

- [ ] Integrate with Qortal Core's peer discovery
- [ ] Map Qortal peer IDs to QLive swarm peer IDs
- [ ] Implement NAT traversal using Qortal's infrastructure
- [ ] Evaluate Reticulum integration for low-overhead routing
- [ ] Test peer connectivity across different network topologies

### Reticulum Research
- [ ] Evaluate Reticulum's suitability for high-bandwidth video
- [ ] Benchmark Reticulum vs. WebRTC for chunk delivery
- [ ] Document Reticulum integration approach
- [ ] Prototype Reticulum-based swarm transport

---

## Minting & Reputation

- [x] Explore integration with Qortal minting weight → [docs/MINTING-INTEGRATION.md](../docs/MINTING-INTEGRATION.md) (phased: off-chain relay reputation now; on-chain minting feed deferred)
- [ ] Design proof-of-relay receipt verification on-chain
- [ ] Implement relay reward distribution via QORT
- [ ] Integrate with Qortal's reputation system
- [x] Document incentive model economics → [docs/ECONOMIC-MODELING.md](../docs/ECONOMIC-MODELING.md)

### Reward Mechanics
- [ ] Define QORT per MB pricing model
- [ ] Implement bounty pool management
- [ ] Handle reward disputes and slashing
- [ ] Test reward distribution scenarios

---

## Qortal Core API

- [ ] Document all Qortal Core endpoints used
- [~] Create a Qortal Core client library → reuse `qapp-core` (`qortalRequest`, `usePublish`, `useResources`) — see [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md)
- [ ] Implement error handling for API failures
- [ ] Handle API version compatibility
- [ ] Test against a running Qortal Core node

### API Endpoints Needed
- [ ] Name registration and resolution
- [ ] QDN publish and retrieve
- [ ] Peer list and connectivity
- [ ] Transaction creation and broadcast
- [ ] Minting status and weight

---

## Testing & QA

- [ ] Test against a local Qortal Core node
- [ ] Test against a testnet node
- [ ] Test against mainnet (read-only first)
- [ ] Test QDN publish/retrieve with real data
- [ ] Test identity verification with real Qortal Names
- [ ] Test peer connectivity in real network conditions

---

## Milestones

- [ ] **C1 — QDN publish/retrieve:** Stream metadata and VOD archives work on QDN
- [ ] **C2 — Identity:** Chunk signing/verification works with Qortal Names
- [ ] **C3 — Peer network:** Swarm works over Qortal's peer infrastructure
- [ ] **C4 — Minting:** Proof-of-relay rewards integrated with minting

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| — | — | — |

---

*This document is a living artifact. Update it as the integration evolves.*