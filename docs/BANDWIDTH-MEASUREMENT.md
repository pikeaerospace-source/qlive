# BANDWIDTH-MEASUREMENT — Research

**Research task:** How to accurately measure peer bandwidth contribution for tit-for-tat and proof-of-relay?

**Status:** In progress (`[~]`)

**Related:** `src/python/qlive/incentives.py`, `src/python/qlive/proof.py`, [protocol.md](protocol.md) §9, [MONETIZATION.md](MONETIZATION.md), [TODO-RESEARCH.md](../TODO-RESEARCH.md) → Security Research

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Research Questions

- [~] What is the right granularity for bandwidth accounting (bytes vs. chunks vs. time)?
- [~] Where should measurement happen (sender, receiver, or both)?
- [~] How to prevent gaming (double-counting, sybil, forged receipts)?
- [x] Quantify the CPU cost of per-chunk accounting primitives (hashing).
- [ ] Design a verifiable, tamper-evident bandwidth receipt.

---

## Findings

### 1. Existing accounting primitives

The codebase already has two relevant mechanisms:

- **`incentives.py` → `BandwidthAccount`:** tracks `bytes_sent`, `bytes_received`, `chunks_sent`, `chunks_received` per peer, and computes a `ratio` (sent/received) for tit-for-tat classification.
- **`proof.py` → `BandwidthReceipt`:** a signed receipt (`relay_node_id`, `downstream_node_id`, `stream_id`, `bytes_relayed`, `timestamp`) that a downstream peer signs to attest a relay served them data.

### 2. Per-chunk hashing cost (measured)

| Bitrate (1s chunk) | Payload | SHA-256 |
| --- | --- | --- |
| 1000 kbps | 125 KB | 71 µs |
| 4500 kbps | 562 KB | 343 µs |
| 6000 kbps | 750 KB | 416 µs |

Hashing each chunk (already required for the `payload_hash` in the header) is cheap and can be reused for accounting. No additional hashing is needed to measure bytes — byte counts are already known from `len(chunk.payload)`.

---

## Analysis

### Granularity

| Granularity | Pros | Cons |
| --- | --- | --- |
| **Bytes** | Precise; maps directly to cost (bandwidth) | Requires accurate counters on both ends |
| **Chunks** | Simple; already tracked | Coarse — a 1s chunk varies from ~125 KB to ~750 KB by bitrate |
| **Time** | Simple | Poor proxy — a connected-but-idle peer looks "contributing" |

**Conclusion:** Measure in **bytes**, but record both bytes and chunk count (chunk count is useful for detecting anomalous/oversized chunks).

### Measurement point

- **Sender-side** counting is vulnerable to the sender inflating their own contribution.
- **Receiver-side** counting is more trustworthy for *what was actually received*, but a colluding sender+receiver can still fabricate a receipt.
- **Proof-of-relay** requires the *downstream* peer to sign a receipt attesting what they received — this is the design already in `proof.py`.

### Gaming vectors

| Vector | Mitigation |
| --- | --- |
| Sender inflates bytes | Receiver signs the receipt (receiver attests bytes actually received) |
| Colluding sender+receiver fabricate receipts | Require receipts to reference real `stream_id` + chunk sequence ranges; dispute window (24h) before redemption |
| Sybil (one node, many identities) | Qortal Name identity + reputation; receipts are only valuable if redeemable against a bounded bounty |
| Double-counting the same bytes | Receipts keyed by `(stream_id, sequence range)`; reject overlapping ranges |
| Replay of old receipts | Timestamp + nonce + dispute window |

---

## Recommendation

1. **Account in bytes at chunk granularity**, using the existing `BandwidthAccount` counters. No extra hashing is required (the `payload_hash` is already computed).
2. **For proof-of-relay, have the downstream peer sign a receipt** attesting `bytes_relayed` (already implemented in `proof.py`). Add a **sequence-range** field to prevent double-counting and make receipts verifiable against the actual stream.
3. **Enforce a dispute window** (already `redemption_delay_seconds = 86400`) before receipts can be redeemed.
4. **Bound the bounty pool** so the total redeemable reward is finite, limiting sybil/fabrication upside.
5. **Separate tit-for-tat (local, social) from proof-of-relay (global, economic):** tit-for-tat uses local byte counters (no receipts, no chain); proof-of-relay uses signed receipts that MAY feed reputation/minting.

---

## Test Results

Benchmark harness: `/tmp/qlive_research_bench.py` (section 6). Full test suite: **266 passed** (including `test_incentives.py` and `test_proof.py`).

---

## Open Questions

- [ ] What is the exact receipt schema for on-chain verification (sequence ranges, merkle commitments)?
- [ ] How to aggregate many micro-receipts into a single redeemable proof without bloating the chain?
- [ ] Should bandwidth measurement be smoothed (EWMA) to avoid oscillation in tit-for-tat classification?
- [ ] What prevents a relay from relaying garbage (valid-signed but useless) data to farm receipts? (Requires content validation, not just byte counting.)

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-14 | Account in bytes; downstream peer signs receipts | Bytes map to cost; receiver attestation resists sender inflation |
| 2026-08-14 | Add sequence-range to receipts | Prevents double-counting and enables verification |

---

*This document is a living artifact. Update it as the receipt schema and on-chain verification are designed.*
