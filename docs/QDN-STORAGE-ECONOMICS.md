# QDN & Blockchain — Storage, Chunk Sizing & Cost Analysis

**Status:** In progress (`[~]`) — resolves the QDN & Blockchain research cluster
in [TODO-RESEARCH.md](../TODO-RESEARCH.md): QDN chunk sizing, transaction costs,
chain-bloat analysis, and storage limits / retention.

**Method:** every quantitative figure below is **derived from the codebase**
(`qlive/signaling.py`, `qlive/archival.py`, the schemas) and reproducible
offline. Items that depend on the live Qortal network (exact publish fee, tx
size, QDN retention) are marked **to verify** and require a running node — see
[QORTAL-CORE-API.md](QORTAL-CORE-API.md).

**Related:** [protocol.md](protocol.md) §4 & §7,
[QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md),
[vod-pipeline.md](vod-pipeline.md), [MONETIZATION.md](MONETIZATION.md) §1,
[MONETIZATION.md](MONETIZATION.md) §11, `qlive/archival.py`.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Findings Summary

| Question | Finding | Verdict |
| --- | --- | --- |
| QDN chunk sizing (10–50 MB) | Archives always flush at the **10 MB floor**; the 50 MB ceiling is unused | **Action needed** — flush toward the ceiling (5× fewer chunks) |
| Transaction costs | ~0.001–0.01 QORT per stream event; archival = 1 standard QDN fee | Negligible (per [MONETIZATION.md](MONETIZATION.md) §11); **fee to verify** |
| Chain bloat | Metadata doc ≈ 0.8–1.1 KB and **data is off-chain**; peer-list publishes are the bloat driver, not ledger size | **Bounded** by delta-triggered cadence |
| Storage limits / retention | Live media never touches QDN; only metadata + final archive. Retention specifics **to verify** | **Open** |

---

## 1. QDN Chunk Sizing (10–50 MB)

QDN data chunks aggregate expired live fragments (see
[vod-pipeline.md](vod-pipeline.md) §1). Sizing is a trade-off between **chunk
count** (more QDN resources → more per-resource overhead and manifest entries)
and **per-chunk granularity** (finer chunks recover/re-serve more cheaply).

### 1.1 Derived geometry

Per-hour QDN data volume and chunk counts at representative bitrates
(video+audio nominal; 1 s fragments):

| Bitrate | GB / hour | 10 MB chunks/h | 50 MB chunks/h | 1 s fragments per 10 MB |
| --- | --- | --- | --- | --- |
| 2.5 Mbps | 1.12 | 113 | 23 | 34 |
| 4.5 Mbps | 2.02 | 203 | 41 | 19 |
| 6.0 Mbps | 2.70 | 270 | 54 | 14 |

Per-chunk integrity overhead is small and constant: `QDNDataChunk.hash` chains
`index(8 B) + previous_hash(32 B) + data`, so **40 bytes of chain metadata per
QDN chunk** (≈ 10 KB across a 2.7 GB / 270-chunk archive — negligible).

### 1.2 The flush-floor finding

`ArchivalPipeline` flushes a QDN chunk when the buffer reaches
`min_chunk_bytes`, which defaults to `QDN_CHUNK_MIN_BYTES` (10 MB);
`max_chunk_bytes` (50 MB) is stored but **never consulted**. Consequently a
large archive is fragmented into ~5× more QDN resources than the protocol's
50 MB ceiling allows, multiplying:

- the number of QDN publish resources / manifest entries,
- per-resource overhead and retrieval round-trips,
- the count of `chunkHashes` entries repeated in the Q-Tube manifest.

**Recommendation:** flush toward `max_chunk_bytes` (e.g. flush when the buffer
reaches the *max*, or the largest fragment boundary below it), keeping
`min_chunk_bytes` only as the "don't emit tiny trailing chunks" floor. This cuts
chunk count ~5× with no change to data volume.

**Evidence:** `src/python/qlive/archival.py` (`add_chunk` → `_flush`,
`min_chunk_bytes`/`max_chunk_bytes`); constants in
[protocol.md](protocol.md) §10.

---

## 2. Chain Footprint (Bloat Analysis)

The key distinction ([QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md) §1):
QDN **publish transactions are on-chain but small**; the **data is off-chain**,
stored and served by QDN nodes. So QLive's chain impact is set by the number and
size of *references*, not by media volume.

### 2.1 Metadata document size

Measured from `StreamMetadata.to_dict()` (compact JSON):

| Doc | Bytes |
| --- | --- |
| Live doc, empty swarm lists | 774 |
| Live doc, 8 tree + 8 mesh peers | 847 |
| Doc with 60 peers | 1,127 |

So a signaling document is **≈ 0.8–1.1 KB**, and the peer list dominates the
size. Live media (`GB/hour`, §1.1) never appears on-chain at all.

### 2.2 Publish events per stream

| Event | Publishes |
| --- | --- |
| Lifecycle (`announced → live → ended → archived`) | up to 4 (state changes) |
| Swarm peer-list refresh (delta-triggered, 30–60 s cap) | ~1 per change while live |
| Key rotation (private streams, 5–10 min) | ~6–12 per hour |

The **peer list is the bloat driver**: a fixed-interval refresh would emit a
snapshot even when nothing changed. Delta-triggering (already the decision) keeps
this proportional to actual churn, and the doc is < 1.2 KB.

**Verdict: bounded.** Even a heavily-churning 1-hour stream emits tens of
sub-KB publishes, not thousands.

**To verify (running node):** actual on-chain tx size (reference + metadata) and
whether QDN re-publishing a resource updates in place or appends a version —
both affect the per-publish ledger cost ([QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md) → Open Questions).

---

## 3. Transaction Costs (QORT)

QLive's cost model is **pay-per-publish-event**, not per-second:

| Item | Cost (per [MONETIZATION.md](MONETIZATION.md)) | Notes |
| --- | --- | --- |
| Qortal Name registration | ~0.01 QORT | One-off, required |
| Stream registration / metadata publish | 0.001–0.01 QORT | Per stream event |
| Swarm peer-list / key-rotation publishes | same per-publish fee | Delta-triggered to bound count |
| VOD archival publish | "standard QDN fee" | Once per archive (manifest + chunks) |

**Total to start streaming:** ~0.02 QORT — negligible
([MONETIZATION.md](MONETIZATION.md) §11).

**Cost model for an archive:** `publishes × fee`, where `publishes` scales with
QDN chunk count (§1). This is the second reason to flush toward 50 MB: fewer
chunks ⇒ fewer archival publishes ⇒ lower archival fee. **The exact per-publish
QORT fee is to verify against a running node** — it is the single input that
turns the model into a number ([QORTAL-CORE-API.md](QORTAL-CORE-API.md),
[QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md) → Open Questions).

---

## 4. Storage Limits & Retention

What QLive actually places on QDN:

- **Live media:** nothing. Fragments live in the RAM sliding-window buffer and
  are never published mid-stream ([buffer-design.md](buffer-design.md)).
- **Signaling metadata:** a < 1.2 KB `qlive-stream` doc per active stream
  (§2.1), re-published on state change / delta triggers.
- **Final archive:** the stitched QDN data chunks (GB-scale, §1.1) plus the
  Q-Tube manifest, published once on stream end ([vod-pipeline.md](vod-pipeline.md)).

**Implications:**

- QLive's *steady-state* QDN footprint per live stream is **kilobytes** — the
  bounded, re-published metadata doc.
- The *durable* footprint is the **archive** only, and only for streamers who
  archive (GB per hour at §1.1 rates). This is the same order as any Q-Tube VOD
  upload, so QLive adds no new storage class.

**To verify (Qortal docs / running node):** QDN per-resource size limits, whether
nodes prune/expire resources and on what schedule, and the storage-cost
expectation for GB-scale archives. QLive's design assumes GB-scale resources are
acceptable because Q-Tube already stores VOD at this size — **confirm this
assumption** before relying on it.

---

## 5. Recommendations

1. **Flush archive chunks toward 50 MB** (not the 10 MB floor) — ~5× fewer QDN
   resources, publishes, and manifest entries, at equal data volume. Keep 10 MB
   as the trailing-chunk floor. *(Code change in `ArchivalPipeline`; tracked as
   the top follow-up.)*
2. **Keep delta-triggered peer-list publishes** (already decided) — this is what
   keeps the §2 publish count bounded; never poll metadata.
3. **Treat the per-publish QORT fee as the one unknown** that converts the cost
   model (§3) into numbers; measure it on a running node.
4. **Confirm QDN accepts GB-scale resources** (§4) before depending on it for
   archival.
5. **No change** to the on-chain vs. off-chain split — the < 1.2 KB metadata doc
   plus off-chain media is already the minimal-footprint design.

---

## 6. Test Results

All figures in §1.1 and §2.1 are reproducible offline:

```bash
cd src/python && python - <<'PY'
import json
from qlive.signaling import StreamMetadata
m = StreamMetadata(publisher="alice", title="t")
print(len(json.dumps(m.to_dict(), separators=(",", ":"))))  # ~774
PY
```

No empirical QDN measurements yet (require a running Qortal Core node).

---

## 7. Open Questions

- [ ] Actual QORT fee per QDN publish transaction? (Turns the cost model into numbers.)
- [ ] Does QDN update a resource in place or append a version per re-publish?
- [ ] QDN per-resource size limit and any pruning/expiry policy?
- [ ] Real on-chain tx size for a metadata publish?
- [ ] Measured QDN publish→retrievable latency (affects peer-list freshness).

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-10-12 | Flush archive chunks toward the 50 MB ceiling, keep 10 MB as the trailing floor | The 10 MB floor made archives ~5× chunkier than the protocol allows; fewer chunks cut QDN resources, publishes, and manifest entries |
| 2026-10-12 | Cost model is pay-per-publish-event; per-publish fee to verify | Live media never touches the chain; only < 1.2 KB metadata + the final archive do |

---

*This document is a living artifact. Update it once QDN publish costs, tx size,
and retention behavior are measured against a running node.*
