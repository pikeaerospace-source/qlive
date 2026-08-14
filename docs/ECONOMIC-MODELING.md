# ECONOMIC-MODELING — Research

**Research task:** Model the QORT economy quantitatively — relay-node economics, streamer economics, viewer economics, proof-of-relay reward design, and free-rider scenarios.

**Status:** Complete (`[x]`)

**Related:** [MONETIZATION.md](MONETIZATION.md) (design), [SWARM-SIMULATION.md](SWARM-SIMULATION.md) (free-rider simulation), `src/python/qlive/proof.py`, `incentives.py`

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [x] Model relay node economics (bandwidth costs vs. rewards).
- [x] Model streamer economics (production costs vs. revenue).
- [x] Model viewer economics (willingness to pay).
- [x] Proof-of-relay: minting vs. reputation vs. tit-for-tat?
- [x] Simulate free-rider scenarios and quantify their cost.

---

## 1. Relay Node Economics

The current reward rate (`proof.py`) is **`qort_per_mb = 0.001` → 1 QORT per GB** relayed.

**Throughput model** (4.5 Mbps stream, 1 s fragments):

| Downstream viewers served | Bandwidth | QORT / hour |
| --- | --- | --- |
| 1 | 4.5 Mbps | 2.03 |
| 8 (full fanout) | 36 Mbps | 16.2 |
| 64 (full subtree, 2 levels) | 288 Mbps | 129.6 |

*(1 GB ≈ 2.25 h of a 4.5 Mbps stream to one viewer.)*

**Cost side:**

| Cost | Magnitude | Notes |
| --- | --- | --- |
| Electricity | ~$0.001/h (10 W @ $0.12/kWh) | Negligible |
| ISP upload | $0 (unmetered) or $0.01–0.05/GB (metered) | Dominant if metered |
| Hardware depreciation | ~$0.01–0.05/h | Small |

**Break-even QORT price** to match AWS egress ($0.09/GB):

```
1 QORT/GB = $0.09/GB  ⟹  QORT ≈ $0.09
```

So at `qort_per_mb = 0.001`, relay rewards are **economically meaningful only
if QORT is worth ~$0.01 or more** — otherwise a relay earns less than the
bandwidth it serves. For **unmetered home connections** (the common case), the
marginal bandwidth cost is zero, so any positive QORT reward is a bonus and
relaying is rational even at low QORT prices.

**Conclusion:** the reward rate is a tunable parameter; it should be set
relative to the QORT price so that a relay serving a full fanout (8 viewers)
earns a meaningful amount (~$0.10–1/h), not a fixed constant.

---

## 2. Streamer Economics

**Fixed costs:** ~0.02 QORT to start (Name registration + START_STREAM, per
MONETIZATION.md) — a negligible barrier.

**Revenue streams** (per MONETIZATION.md §2):

| Stream | Model | Example (100 viewers) |
| --- | --- | --- |
| Tips / superchats | 1–5% of viewers tip | 5 tips × 0.1 QORT = 0.5 QORT |
| Pay-per-view | 1 QORT/viewer, 20% convert | 20 × 1 QORT = 20 QORT |
| Subscriptions | 1 QORT/month, 10% subscribe | 10 QORT/month |

**Production cost** is the streamer's time + equipment (sunk). The marginal
cost per stream is ~0 (the ~0.02 QORT registration is covered by the first
tip). So **streaming is profitable from the first viewer** — the economics
favor long-tail creators, unlike centralized platforms that take 30–50%.

---

## 3. Viewer Economics

- **Free public streams** are the default; viewing costs $0 (the broadcaster
  pays the ~0.02 QORT registration).
- **Pay-per-view** requires willingness-to-pay (WTP) > price. For a 1 QORT
  PPV stream, a viewer pays if the content value exceeds 1 QORT. WTP is
  bounded by opportunity cost and the price of substitutes (free streams).
- **Micro-tipping** friction matters: tips are batched (5-min settlement) to
  avoid per-tip transaction overhead.

**Key constraint:** viewers will not pay for content that is freely available
elsewhere. PPV only works for **exclusive** content; tips work for
**appreciation**; subscriptions work for **recurring** content. The three
mechanisms serve different viewer motivations.

---

## 4. Proof-of-Relay Economics (minting vs. reputation vs. tit-for-tat)

The open question: should relay rewards be minting-weight-based,
reputation-based, or purely social (tit-for-tat)?

| Model | Pros | Cons |
| --- | --- | --- |
| **Tit-for-tat (social)** | Zero chain cost; local; already implemented (`incentives.py`) | Doesn't reward *relays* (only deters free-riders); no economic incentive to run a relay |
| **Reputation-based** | Rewards long-term good actors; sybil-resistant | Subjective; needs on-chain reputation tracking |
| **Minting-weight-based** | Direct economic reward; aligns with Qortal consensus | Requires Qortal Core integration; gaming risk |

**Recommendation — hybrid, in two tiers:**

1. **Tit-for-tat for viewers** (social, local): deters free-riding among
   viewers, who are not expected to be relays. Already implemented.
2. **Proof-of-relay for relays** (economic): relays collect downstream-signed
   receipts and redeem them against a bounded bounty pool. This is the
   *economic* incentive for running a relay, which tit-for-tat cannot provide.

Minting-weight integration is **future work** (requires Qortal Core); the
receipt format is already designed so it *can* feed minting/reputation later
(see SECURITY-MODEL.md §3).

**What prevents gaming:** downstream-signed receipts (a relay can't self-forge),
a 24 h dispute window, and a **bounded bounty pool** (the total redeemable
reward is finite, so fabrication upside is capped).

---

## 5. Free-Rider Economics

Free-riders consume bandwidth without contributing. In QLive they manifest in
two places:

1. **Tree:** free-riders are leaves and don't forward — but honest leaf
   viewers don't forward either, so tree-wise free-riders are indistinguishable.
2. **Mesh:** free-riders don't serve retransmission requests, shifting the
   recovery load onto honest peers.

**Simulation results** (from SWARM-SIMULATION.md, 5% loss):

| Free-rider fraction | Recovery rate | Delivery rate |
| --- | --- | --- |
| 0% | 97.0% | 99.6% |
| 25% | 98.9% | 99.9% |
| 50% | 94.7% | 99.2% |
| 75% | 74.2% | 96.9% |
| 100% | 30.3% | 91.9% |

**Subsidy model:** with free-rider fraction `f` and mesh size `M`, the
probability a retransmission request hits only free-riders (and thus fails)
is roughly `f^M` per attempt. At `f = 0.75, M = 4`, that's `0.75⁴ ≈ 0.32` —
matching the observed recovery collapse.

**Conclusion:** free-riders only impose a real cost once they dominate the
mesh (>50%). Tit-for-tat should target the *worst* offenders (the top decile
of non-contributors) rather than trying to exclude all non-contributors, which
would also punish honest leaf viewers who legitimately have little to upload.

---

## Recommendations

1. **Tune `qort_per_mb` relative to the QORT price** so a full-fanout relay
   earns a meaningful amount (~$0.10–1/h), not a fixed constant.
2. **Keep the bounty pool bounded** — it is the primary defense against
   reward farming.
3. **Two-tier incentives:** tit-for-tat for viewers, proof-of-relay for relays.
4. **Target the worst free-riders** (>50% free-riders is the threshold where
   recovery collapses).
5. **Defer minting integration** until Qortal Core is available; the receipt
   format is already compatible.

---

## Open Questions

- [ ] What is the current QORT price? (Needed to set `qort_per_mb`.)
- [ ] Should the bounty pool be per-stream or global?
- [ ] What is the optimal `qort_per_mb` to balance relay incentive vs. streamer cost?
- [ ] Does a relay bond improve security enough to justify the friction?

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Two-tier incentives (tit-for-tat + proof-of-relay) | Tit-for-tat deters viewers; only proof-of-relay rewards relays economically |
| 2026-08-14 | Bounded bounty pool is the primary anti-farming defense | Caps fabrication upside |
| 2026-08-14 | Target worst free-riders, not all non-contributors | >50% free-riders is the collapse threshold; honest leaves legitimately upload little |

---

*This document is a living artifact. Update it as the economy is tuned.*

