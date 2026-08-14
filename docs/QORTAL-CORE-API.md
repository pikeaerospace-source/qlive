# QORTAL-CORE-API — Research

**Research task:** What existing Qortal Core endpoints can be reused (QDN publish, name registration, peer discovery)?

**Status:** In progress (`[~]`)

**Related:** [TODO-QORTAL-CORE.md](../TODO-QORTAL-CORE.md), `src/python/qlive/signaling.py`, [QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md)

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] Which Qortal Core REST endpoints map to QLive's signaling needs?
- [~] Which WebSocket topics provide real-time updates?
- [~] What are the QDN resource naming conventions for streams?
- [ ] Verify each endpoint against a running Qortal Core node.
- [ ] Document QDN data size limits and publish fees.

---

## Findings

### 1. Qortal Core API surface

Qortal Core exposes a REST API (default port `12391`, loopback-only by default per `settings.json`) plus WebSocket endpoints. The API is implemented as JAX-RS resource classes under `src/main/java/org/qortal/api/resource/` in the `Qortal/qortal` repository. Relevant resource classes observed include:

| Resource class | Likely path | QLive use |
| --- | --- | --- |
| `ArbitraryResource` | `/arbitrary` | QDN publish/retrieve (stream metadata, VOD chunks, key envelopes) |
| `NamesResource` | `/names` | Name registration/resolution (publisher identity → public key) |
| `PeersResource` | `/peers` | Peer discovery (seed swarm connectivity) |
| `AddressesResource` | `/addresses` | Address ↔ public key resolution |
| `TransactionsResource` | `/transactions` | Transaction creation/broadcast (publish, payments) |
| `StatsResource` | `/stats` | Node stats (uptime, minting status) |

> ⚠️ These paths are from the Qortal Core codebase layout and general Qortal API knowledge. **Exact paths, methods, and parameters must be verified against a running node** (see Verification below).

### 2. QDN (Arbitrary Data) publish/retrieve

QDN arbitrary data is the mechanism for storing stream metadata and VOD archives. The expected endpoints (to verify):

- `POST /arbitrary` — publish data (with `name`, `service`, `identifier`, `data`, `filename`, etc.).
- `GET /arbitrary/{service}/{name}/{identifier}` — retrieve a specific resource.
- `GET /arbitrary/resources?service=...&name=...` — list resources.
- `GET /arbitrary/resource/status/{service}/{name}/{identifier}` — check replication status.

### 3. Name registration/resolution

- `POST /names` — register a Qortal Name.
- `GET /names/{name}` — resolve a name (returns owner address/public key).

QLive maps the broadcaster's **Qortal Name → Ed25519 public key** for chunk-signature verification.

### 4. Peer discovery

- `GET /peers` — connected peers.
- `GET /peers/known` — known peers (candidate seed nodes).

QLive can seed its swarm connectivity from Qortal's own peer list.

### 5. WebSocket

Qortal Core provides WebSocket topics (e.g., for chat, transactions, and arbitrary-data broadcast). QLive would use a WebSocket subscription to receive QDN resource updates in near-real-time (e.g., a new stream metadata document or peer-list update), rather than polling.

---

## Analysis: Mapping QLive needs → Qortal Core

| QLive need | Qortal Core mechanism |
| --- | --- |
| Publish stream metadata | `POST /arbitrary` (QDN, service `QLIVE`, name = publisher, identifier = stream id) |
| Discover active streams | `GET /arbitrary/resources?service=QLIVE` + WebSocket subscription |
| Resolve publisher identity | `GET /names/{name}` → public key |
| Publish VOD archive | `POST /arbitrary` (QDN chunks) + Q-Tube manifest |
| Seed swarm peers | `GET /peers/known` |
| Relay rewards / payments | `POST /transactions` (QORT transfer) |

---

## Recommendation

1. **Build a thin Qortal Core client** (the `signaling.py` `StreamRegistry` is currently an in-memory stand-in — replace it with real QDN calls).
2. **Adopt a QDN resource naming convention** for streams, e.g.:
   - service: `QLIVE`
   - name: publisher Qortal Name
   - identifier: `streamId` (SHA-256 hex) for metadata; `streamId/archive/0001` etc. for VOD chunks.
3. **Use WebSocket subscriptions** for real-time signaling updates instead of polling.
4. **Verify every endpoint** against a local Qortal Core node before wiring into production code (see Verification).

---

## Verification (TODO)

- [ ] Stand up a local Qortal Core node (Docker: `docker compose up -d`).
- [ ] Confirm exact `POST /arbitrary` request body and required fields.
- [ ] Confirm `GET /arbitrary/resources` query parameters and response shape.
- [ ] Confirm name resolution returns the Ed25519 public key.
- [ ] Measure QDN publish/retrieve latency and fees (feeds QDN-SIGNALING-FREQUENCY.md).
- [ ] Confirm WebSocket topic names for arbitrary-data updates.

---

## Open Questions

- [ ] What is the exact QDN resource size limit (does it align with QLive's 10–50 MB chunk target)?
- [ ] What is the QORT fee for a QDN publish transaction?
- [ ] Does QDN support versioned updates of a resource, or is each publish a new resource?
- [ ] Is the API loopback-only by default, and what whitelist change is needed for remote QLive nodes?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Replace in-memory `StreamRegistry` with a real Qortal Core QDN client | Current code is a stand-in; QDN is the authoritative signaling layer |
| 2026-08-14 | Adopt `QLIVE` service + `streamId` identifier naming | Unambiguous, discoverable, aligns with QDN conventions |

---

*This document is a living artifact. Update it once endpoints are verified against a running Qortal Core node.*
