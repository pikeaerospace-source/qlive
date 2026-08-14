# QDN-SIGNALING-FREQUENCY — Research

**Research task:** How often should swarm peer lists be refreshed on QDN without bloating the chain?

**Status:** In progress (`[~]`)

**Related:** [protocol.md](protocol.md) §4.3, `src/python/qlive/signaling.py`, [TODO-RESEARCH.md](../TODO-RESEARCH.md) → QDN & Blockchain

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] What is the optimal swarm peer-list refresh cadence?
- [~] What actually "bloats" — the ledger or QDN storage?
- [~] Delta updates vs. full peer-list snapshots?
- [ ] Estimate QORT cost of stream registration + peer-list updates.
- [ ] Measure QDN publish/retrieve latency for signaling updates.

---

## Findings

### 1. Clarifying "chain bloat"

It is important to distinguish two layers:

- **Qortal ledger (blocks):** QDN *publish transactions* are on-chain and small (a reference + metadata), but the **data itself is stored off-chain** by QDN nodes, not in blocks. So frequent peer-list updates do **not** bloat the ledger the way on-chain data would.
- **QDN storage:** each update creates a new QDN resource (or version) that nodes must store and serve. Frequent updates therefore bloat **QDN storage/bandwidth**, not the ledger.

The real cost of frequent updates is therefore: (a) QDN storage churn, (b) publish transaction fees (small QORT), and (c) propagation latency — not ledger size.

### 2. Current spec (protocol.md §4.3)

| Update | Frequency |
| --- | --- |
| Stream metadata | On state change (announce/start/end/archive) |
| Swarm peer list | Every 30–60s |
| Encryption key rotation | Every 5–10 min |

### 3. Peer-list churn

Peer lists change as viewers join/leave. A 30–60s full-snapshot cadence means every join/leave is batched into the next snapshot, but a snapshot is published even when nothing changed, and a snapshot can be stale for up to the interval.

---

## Analysis

| Cadence | Pros | Cons |
| --- | --- | --- |
| < 30s | Fresh peer lists; fast discovery | High QDN churn; more fees; marginal benefit |
| 30–60s | Good freshness; bounded churn | Up to 60s stale on join/leave |
| > 60s | Low churn | Stale peer lists; viewers may connect to departed peers |

**Key insight:** the peer list is a *hint* for discovery, not a hard requirement for connectivity — the swarm itself handles churn via health checks and mesh fallback. So the peer list does not need to be perfectly fresh.

---

## Recommendation

1. **Publish the swarm peer list every 30–60s**, but **only when membership actually changed** (delta-triggered, not fixed-interval). This avoids publishing identical snapshots.
2. **Use delta updates** for large swarms: publish only the set of added/removed peers since the last snapshot, with a full snapshot every N updates (e.g., every 5 min) as a checkpoint.
3. **Keep stream metadata on state-change only** (already correct) — never poll metadata.
4. **Decouple key rotation (5–10 min) from peer-list cadence** — they have different freshness requirements.
5. **Treat the peer list as a discovery hint**, not an authoritative membership list; rely on health checks + mesh fallback for correctness.

---

## Test Results

No empirical QDN measurements yet (requires a running Qortal Core node — see QORTAL-CORE-API.md). The following are **to be measured**:

- [ ] QDN publish latency (time from publish to retrievable).
- [ ] QORT fee per publish transaction.
- [ ] QDN storage cost per peer-list update (bytes).

---

## Open Questions

- [ ] What is the actual QORT fee for a QDN publish transaction? (Determines the economic cost of cadence.)
- [ ] Does QDN support in-place resource updates, or does each update create a new resource/version?
- [ ] What is the QDN propagation latency across the network (affects how "fresh" a published list actually is)?
- [ ] Should peer-list updates be signed by the broadcaster only, or by a quorum of tree nodes?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Delta-triggered updates (30–60s cap), not fixed-interval | Avoids publishing unchanged snapshots; bounds staleness |
| 2026-08-14 | Treat peer list as a discovery hint | Swarm handles churn via health checks + mesh fallback |

---

*This document is a living artifact. Update it once QDN publish costs and latency are measured against a running node.*
