# SECURITY-MODEL — Research

**Research task:** Evaluate sybil resistance, DoS resilience, proof-of-relay receipt-forgery resistance, and key distribution for private streams.

**Status:** Complete (`[x]`)

**Related:** [THREAT-MODEL.md](THREAT-MODEL.md), [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md), `src/python/qlive/incentives.py`, `proof.py`, `buffer.py`

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [x] **Sybil resistance:** Does Qortal Name-based identity resist sybil attacks?
- [x] **DoS resilience:** What rate limiting / abuse prevention is needed?
- [x] **Receipt forgery:** How resistant is the proof-of-relay receipt format?
- [x] **Key distribution:** How to distribute keys for private streams?

---

## 1. Sybil Resistance

QLive identities are **Qortal Names**, which require a registration fee (paid
in QORT). This makes sybil identities *costly*, not impossible.

**Cost model.** Let `F` be the Qortal Name registration fee and `N` the number
of sybil identities an attacker wants. The attacker's cost is `N × F` (plus
`N ×` node resources). The attack is only rational if its payoff exceeds
`N × F`.

Two payoff scenarios:

1. **Eclipse / swarm dominance** — the attacker gains influence over a swarm.
   Payoff is qualitative (censorship, selective drop), bounded by the value of
   the target stream.
2. **Reward farming** — the attacker fabricates proof-of-relay receipts. The
   total redeemable reward is bounded by the stream's **bounty pool** `B`, so
   farming is unprofitable when `N × F > B`.

**Conclusion:** Qortal Name identity provides *economic* sybil resistance —
it raises the cost of each identity rather than preventing them outright. The
resistance is only as strong as the registration fee relative to the reward
pool, so the **bounty pool must be kept bounded** and the fee must be
non-trivial. (The exact fee `F` must be measured against a running node — see
QORTAL-CORE-API.md.)

---

## 2. DoS Resilience

| Vector | Mitigation | Status |
| --- | --- | --- |
| Chunk flooding | Signature verification is cheap (~1 ms/chunk) and rejects unsigned chunks before buffering | Implemented (`chunk.py`) |
| Request flooding | Retransmission requests are rate-limited and bounded by `max_attempts` | Implemented (`retransmit.py`) |
| Free-rider bandwidth drain | Tit-for-tat deprioritizes/disconnects non-contributors | Implemented (`incentives.py`) |
| Oversized chunks | Buffer memory ceiling (256 MB) + chunk-size validation | Implemented (`buffer.py`) |
| Peer flooding (join storm) | Health checks + QDN peer-list gating | Designed (needs network) |

**Tit-for-tat thresholds** (`incentives.py`): a peer is a *free-rider* below
`free_rider_threshold = 0.1` (sent/received ratio), *contributing* above
`contributing_threshold = 0.8`, and is warned up to `max_free_rider_warnings = 3`
times before disconnection (with a 300 s inactivity timeout).

**Gaming note:** an attacker can contribute just enough to stay above the
0.1 threshold ("strategic free-riding"). The thresholds are tunable; the
simulation (SWARM-SIMULATION.md) shows free-riders only matter when they
dominate the mesh (>50%), so tit-for-tat should target the *worst* offenders
rather than all non-contributors.

---

## 3. Receipt Forgery Resistance

The proof-of-relay receipt (`proof.py`) is signed by the **downstream node**,
not the relay:

```
signing_data = relay_id | downstream_id | stream_id | bytes_relayed | timestamp
```

This gives the following properties:

| Attack | Resistance |
| --- | --- |
| Relay forges its own receipt | ✗ impossible — needs the downstream's Ed25519 key |
| Relay + downstream collude to inflate bytes | ⚠ possible; bounded by dispute window (24 h) + bounty pool |
| Replay an old receipt | ✗ prevented — redemption marks the receipt `REDEEMED` |
| Double-count the same bytes | ⚠ not yet prevented — receipts lack a sequence-range field |

**Recommendations:**

1. **Add a `sequence_range` field** to receipts so overlapping claims can be
   rejected (prevents double-counting) — currently a gap.
2. **Bound the bounty pool** so total redeemable reward is finite (limits
   collusion upside).
3. **Keep the 24 h dispute window** (already `redemption_delay_seconds = 86400`)
   so fabricated receipts can be challenged before redemption.
4. **Optionally require a relay bond** — a stake forfeited on proven forgery
   (open question).

---

## 4. Key Distribution (private streams)

Per [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md), private streams use a
**per-stream symmetric key** (AES-256-GCM) distributed via a **hybrid key
envelope**:

1. The broadcaster generates a random AES-256-GCM key per stream.
2. For each authorized viewer, the key is wrapped in an asymmetric envelope
   (X25519 + HKDF / HPKE, or ECIES over secp256k1 to reuse Qortal keys).
3. Envelopes are published to QDN; each viewer unwraps only its own.
4. The key rotates every 5–10 min; each rotation publishes a new envelope set.

**Properties:** the data plane stays multicast-efficient (relays forward
ciphertext without the key); authorization is per-viewer; revocation = re-key
+ re-distribute (a viewer excluded at rotation loses access).

**Open:** which asymmetric scheme (HPKE vs. ECIES) and whether to reuse the
Qortal Name key or a separate encryption key.

---

## Recommendations

1. **Keep the bounty pool bounded** so sybil/receipt-farming upside is finite.
2. **Add a `sequence_range` field to receipts** to prevent double-counting.
3. **Keep the 24 h dispute window** and consider a relay bond for high-value streams.
4. **Tit-for-tat targets the worst free-riders** (only >50% free-riders hurt — see SWARM-SIMULATION.md).
5. **Implement per-stream AES-256-GCM + hybrid key envelopes** for private streams (benchmarked at ~800+ MB/s, a non-issue for throughput).
6. **Measure the Qortal Name registration fee** to quantify the sybil cost model.

---

## Open Questions

- [ ] What is the Qortal Name registration fee `F`? (Quantifies sybil cost.)
- [ ] HPKE vs. ECIES for key envelopes? Reuse the Qortal Name key or a separate key?
- [ ] Is a relay bond necessary, or is the dispute window + bounty cap sufficient?
- [ ] What rate-limit parameters (requests/s, bytes/s) per node?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Sybil resistance is economic (registration fee), not absolute | Qortal Names raise per-identity cost; resistance depends on fee vs. reward |
| 2026-08-14 | Receipts signed by downstream node + dispute window + bounded bounty | Relay cannot self-forge; collusion upside is bounded |
| 2026-08-14 | Hybrid key envelopes (per-stream symmetric + per-viewer asymmetric) | Multicast-efficient data plane + per-viewer authorization |

---

*This document is a living artifact. Update it as the security model evolves.*

