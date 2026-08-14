# Incentives

**Status:** Reference — mirrors `qlive/incentives.py`, `qlive/proof.py` and `protocol.md` §9.

Two complementary mechanisms keep the swarm honest.

---

## Tit-for-Tat (social)

`qlive/incentives.py` tracks per-peer bandwidth and classifies peers:

| Class | Sent/received ratio |
| --- | --- |
| Contributing | ≥ 0.8 |
| Neutral | 0.1–0.8 |
| Free-rider | < 0.1 |

Free-riders are deprioritized and, after 3 warnings, disconnected (300 s
inactivity timeout). This deters *viewers* from leeching.

## Proof-of-Relay (economic)

`qlive/proof.py` — a relay collects a **downstream-signed** receipt attesting
bytes relayed, then redeems it (after a 24 h dispute window) against a bounded
bounty pool. This is the *economic* incentive for running a relay, which
tit-for-tat cannot provide.

The receipt now includes a `start_sequence`/`end_sequence` range so overlapping
claims (double-counting) are rejected.

---

## Economics (from ECONOMIC-MODELING.md)

- Reward: `qort_per_mb = 0.001` → 1 QORT/GB; tune relative to the QORT price.
- Two-tier: tit-for-tat for viewers, proof-of-relay for relays.
- Minting-weight integration is future work (Qortal Core).

---

*See [protocol.md](protocol.md) §9 and [ECONOMIC-MODELING.md](ECONOMIC-MODELING.md) for details.*
