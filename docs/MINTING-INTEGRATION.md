# MINTING-INTEGRATION — Research & Design

**Research task:** Explore integrating QLive's proof-of-relay with Qortal minting
weight / node reputation. Reference [TODO.md](../TODO.md) → Phase 4
("Explore integration with Qortal minting weight / node reputation") and
[TODO-QORTAL-CORE.md](../TODO-QORTAL-CORE.md) → Minting & Reputation.

**Status:** Complete (`[x]`) — design & recommendation; implementation of the
on-chain (minting) leg is deferred until Qortal Core is available.

**Related:** [ECONOMIC-MODELING.md](ECONOMIC-MODELING.md),
[SECURITY-MODEL.md](SECURITY-MODEL.md), `src/python/qlive/proof.py`,
`src/python/qlive/incentives.py`, [QORTAL-CORE-API.md](QORTAL-CORE-API.md).

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [x] Can proof-of-relay receipts feed Qortal minting weight? What is required?
- [x] What is the cleanest on-chain vs. off-chain split, given QLive's
      no-chain-bloat principle?
- [x] How can relay **reputation** be represented without requiring Qortal Core?
- [x] What are the gaming / farming risks and their mitigations?
- [ ] Verify the exact Qortal minting-weight mechanics & API against a running
      node (deferred — see [QORTAL-CORE-API.md](QORTAL-CORE-API.md)).

---

## Findings

### 1. QLive's incentive recap (two-tier)

| Tier | Mechanism | Scope | Implemented |
| --- | --- | --- | --- |
| Viewers | Tit-for-tat (bandwidth accounting, free-rider throttling) | `incentives.py` | Yes |
| Relays | Proof-of-relay — downstream-signed bandwidth receipts redeemed against a **bounded bounty pool** | `proof.py` | Yes |

*Relays* are the only economically incentivized class; tit-for-tat cannot
reward them (a viewer's "upload" is the relay's service). See
[ECONOMIC-MODELING.md](ECONOMIC-MODELING.md).

### 2. The receipt format is already reputation-ready

`proof.py` `BandwidthReceipt` carries: `relay_node_id`, `downstream_node_id`,
`stream_id`, `bytes_relayed`, `timestamp`, and a `start_sequence`/
`end_sequence` range (overlap rejection already implemented and tested). It is
signed by the **downstream** node, so a relay cannot self-forge. These four
properties are exactly what a reputation ledger needs:

- **Attribution** — which node served how much, to distinct downstream peers.
- **Integrity** — signature verifiable against the downstream node's key.
- **Double-count resistance** — sequence ranges reject overlapping claims.
- **Recency** — timestamp enables decay / time-weighted scores.

### 3. The minting-weight question

Qortal mints QORT to accounts based on **minting weight** (a function of an
account's balance, minting power / effective level, and reward-share
relationships), computed on-chain per account. This is fundamentally different
from QLive receipts, which are **off-chain swarm data**. Bridging them requires
an **oracle-style commitment**: something that commits the off-chain reputation
to a form the on-chain minting logic can consume.

> ⚠️ The precise minting-weight formula and whether it can consume external
> reputation data is **not assumed here** — it must be verified against a
> running Qortal Core node ([QORTAL-CORE-API.md](QORTAL-CORE-API.md), currently
> `[~]`). This document only reasons about the design options and picks a
> phased path that does not depend on that unknown.

### 4. The key tension: chain bloat vs. verifiability

Writing every receipt (or even per-batch receipts) to the chain would violate
QLive's core "no chain bloat" design principle (storage/bandwidth on QDN nodes,
fees per transaction, propagation latency — see
[QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md)). A full
on-chain-receipts approach is therefore **rejected**.

---

## Analysis: Integration options

| Option | Offline-capable now? | Chain impact | Security | When |
| --- | --- | --- | --- | --- |
| **A. Off-chain relay reputation** (QLive-internal score from verified receipts) | Yes | none | moderate | Now |
| **B. Reputation-driven routing** (prioritize contributing relays in tree/mesh, fair bounty ordering) | Yes | none | — | Now |
| **C. Bonded relays** (QORT deposit, slashed on proven forgery) | Design only | 1 tx per bond | high | After identity/dispute layer |
| **D. Minting-weight feed** (on-chain commitment/oracle consumed by minting) | No — needs Qortal Core | per commitment | high | Deferred |

### A. Off-chain relay reputation (recommended first step)

Maintain a per-node reputation score derived from **verified, redeemed
receipts** (reusing `ProofOfRelayManager`). Key design points to resist gaming:

- **Time-weighted / decaying score** (e.g., exponential moving average) so a
  one-shot boost does not linger.
- **Diversity-weighted** — require deliveries to *distinct* downstream peers
  across *distinct* streams, so a relay cannot inflate its score via a small
  colluding cohort.
- **Capped contribution** — mirror the **bounded bounty pool**
  (SECURITY-MODEL.md §1): a finite reward/reputation pool keeps fabrication
  upside finite.
- **Dispute window** — reuse `redemption_delay_seconds = 86400` so bad claims
  can be challenged before they count toward reputation.

This needs **no Qortal Core** — it is fully offline/implementable in QLive.

### B. Consumer of reputation (off-chain)

The score feeds local, social decisions rather than money:

- **Routing priority**: prefer high-reputation relays when (re)selecting tree
  parents / mesh peers (a *cooperative* alignment with the existing swarm
  health/rebalance logic — see `swarm.py`).
- **Bounty fairness**: order/rate-limit bounty claims by reputation so reliable
  relays are served first.

### C. Bonded relays (optional hardening)

Require a relay to post a QORT **bond** (via a short transaction; see
[QORTAL-CORE-API.md](QORTAL-CORE-API.md) → TransactionsResource) that is
forfeited on a proven-forgery dispute. This adds skin-in-the-game and raises
the sybil cost captured in [SECURITY-MODEL.md](SECURITY-MODEL.md) §1. It is a
design that depends on a working dispute/arbitration mechanism and should be
added only once identity + QDN signaling are live.

### D. Minting-weight integration (deferred)

A future Qortal Core capability could consume a committed reputation snapshot
to nudge a relay's effective minting weight. Design implications to keep
**rework-free** now:

- Keep receipts **individually verifiable and range-checked** so a later
  commitment only has to reference a *root/merkle* of receipts, not re-prove
  each one.
- Prefer **sparse, delta commitments** (per batch / periodic) over per-receipt
  writes — consistent with [QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md).
- Flag the exact mechanism (minting weight formula, oracle interface, whether
  external reputation is even consumable) as **to-verify** against a real node.

---

## Recommendation

Adopt a **phased** approach:

1. **Now (offline-capable):** implement an off-chain relay **reputation
   tracker** (`reputation.py` / extend `proof.py`) derived from verified
   receipts, with decay + diversity + cap. Expose a score for routing priority
   and bounty ordering. *(Tracked as the natural next code task — see Open
   Questions → next steps.)*
2. **Optional hardening:** bonded relays with slashing on proven forgery, once
   the dispute/identity layer exists.
3. **Deferred:** minting-weight feed, gated on Qortal Core availability and
   verification of the minting mechanics. Keep the receipt/commitment format
   rework-free per Option D.

This mirrors the existing `ECONOMIC-MODELING.md` stance ("Defer minting
integration until Qortal Core is available; the receipt format is already
compatible").

---

## Open Questions / Next Steps

- [ ] Verify the exact Qortal minting-weight formula & whether external
      reputation is consumable (running node).
- [ ] Implement the off-chain relay reputation tracker + tests (first step of
      the recommendation).
- [ ] Is a relay bond necessary, or is the dispute window + bounded pool + cap
      sufficient? (Mirrors [SECURITY-MODEL.md](SECURITY-MODEL.md).)
- [ ] Reputation decay/diversity parameters.

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-30 | Phase integration: off-chain relay reputation now; bonded relays optional; minting-weight feed deferred to Qortal Core | Reputation is offline-capable and needs no chain writes; minting requires an on-chain oracle only meaningful once Qortal Core exposes it; aligns with no-chain-bloat and ECONOMIC-MODELING |

---

*This document is a living artifact. Update it once Qortal Core minting
mechanics are verified against a running node.*