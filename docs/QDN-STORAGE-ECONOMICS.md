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
| QDN chunk sizing (10–50 MB) | Was flushing at the **10 MB floor**; now flushes toward the 50 MB ceiling, published as `service: FILE` (cap `MAX_FILE_SIZE` = 2 GiB) | **Resolved** |
| Transaction costs | ~0.001 QORT base per publish, **proportional to data size** (API example: 0.001 QORT for a small resource); archival = 1 standard QDN fee | Negligible; **scale factor to verify** |
| Chain bloat | Metadata doc ≈ 0.8–1.1 KB and **data is off-chain**; peer-list publishes are the bloat driver, not ledger size | **Bounded** by delta-triggered cadence |
| Storage limits / retention | Per-service **maximums** (FILE: none → 2 GiB `MAX_FILE_SIZE`; APP/ATTACHMENT 50 MB; IMAGE 10 MB; JSON 25 KB; MAIL 1 MB; THUMBNAIL 500 KB); **no minimum**. Retention **to verify** | **Resolved (limits)** |

---

## 1. QDN Chunk Sizing (10–50 MB)

QDN data chunks aggregate expired live fragments (see
[vod-pipeline.md](vod-pipeline.md) §1). Sizing is a trade-off between **chunk
count** (more QDN resources → more per-resource overhead and manifest entries)
and **per-chunk granularity** (finer chunks recover/re-serve more cheaply).

> **QDN enforces per-service maximums, not a minimum** (§4). So the 10 MB floor
> is a **QLive batching policy**, and a short final chunk is valid on QDN.

### 1.1 Derived geometry

Per-hour QDN data volume and chunk counts at representative bitrates
(video+audio nominal; 1 s fragments):

| Bitrate | GB / hour | chunks/h @ 10 MB (old floor) | chunks/h @ 50 MB (new ceiling) | 1 s fragments / 50 MB chunk |
| --- | --- | --- | --- | --- |
| 2.5 Mbps | 1.12 | 113 | 23 | 168 |
| 4.5 Mbps | 2.02 | 203 | 41 | 93 |
| 6.0 Mbps | 2.70 | 270 | 54 | 70 |

Per-chunk integrity overhead is small and constant: `QDNDataChunk.hash` chains
`index(8 B) + previous_hash(32 B) + data`, so **40 bytes of chain metadata per
QDN chunk** (≈ 10 KB across a 2.7 GB / 270-chunk archive — negligible).

### 1.2 The flush-floor finding

`ArchivalPipeline` flushed a QDN chunk as soon as the buffer reached
`min_chunk_bytes`, which defaults to `QDN_CHUNK_MIN_BYTES` (10 MB);
`max_chunk_bytes` (50 MB) was stored but **never consulted**. Consequently a
large archive was fragmented into ~5× more QDN resources than the protocol's
50 MB ceiling allows, multiplying:

- the number of QDN publish resources / manifest entries,
- per-resource overhead and retrieval round-trips,
- the count of `chunkHashes` entries repeated in the Q-Tube manifest.

**Implemented:** the pipeline now flushes **toward the ceiling** — it drains the
buffer just before adding a fragment that would push it past
`max_chunk_bytes`, so every emitted chunk is sized toward the ceiling and stays
within `[min_chunk_bytes, max_chunk_bytes]` (the final chunk from `finalize()`
may be smaller). This cuts chunk count ~5× with no change to data volume.

A remainder below the floor can then appear as a short final chunk. Since QDN
imposes **no minimum resource size** (§4), the default is to emit it
(`FinalChunkPolicy.ALLOW_SHORT`). Deployments that impose their own floor can set
`FinalChunkPolicy.MERGE`, which folds a sub-floor remainder into the previous
chunk (that chunk may then exceed the ceiling by up to `min_chunk_bytes - 1`).

**Evidence:** `src/python/qlive/archival.py` (`add_chunk` → `_flush`,
`min_chunk_bytes`/`max_chunk_bytes`); constants in
[protocol.md](protocol.md) §10; `tests/python/test_archival.py`
(`test_flush_toward_ceiling`, `test_multiple_flushes`,
`test_chunks_never_exceed_ceiling`).

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

### 4.1 QDN resource limits (sourced)

Per Qortal's QDN docs and Core source, limits are **per-service maximums** — there
is **no stated minimum**:

| Service | Max size |
| --- | --- |
| FILE / FILES | **no per-service cap** → bounded by `ArbitraryDataFile.MAX_FILE_SIZE` = **2 GiB** |
| APP, ATTACHMENT | 50 MB |
| IMAGE | 10 MB |
| QCHAT_ATTACHMENT, MAIL | 1 MB |
| THUMBNAIL | 500 KB |
| JSON | 25 KB |
| CHAIN_DATA | 239 B (fully on-chain) |
| VIDEO, AUDIO, DOCUMENT | not confirmed — **to verify** |

- **Qortal chunks arbitrary data internally** at `ArbitraryDataFile.CHUNK_SIZE` =
  **512 KiB** (max `MAX_CHUNK_SIZE` = 1 MiB). This is transparent to publishers —
  a resource is addressed as one unit.
- **`MAX_FILE_SIZE` = 2 GiB** is the ceiling for a single resource.
- Resources **< 240 bytes** can live **fully on-chain**; larger payloads are
  stored off-chain and verified by an on-chain SHA-256 hash.
- Large files should be **chunked**, or published as the **FILE** service.

**Consequences for QLive:**

- **Archive chunks are published under `service: FILE`** — a single file with no
  per-service cap. The binding ceiling is `MAX_FILE_SIZE` = **2 GiB**; QLive keeps
  a **50 MB** operational ceiling (enforced `≤ 2 GiB` in `ArchivalPipeline`) for
  in-RAM chunks and finer manifest / partial-retrieval granularity. See §5.
- The **signaling doc** is published as `service: JSON` → its **25 KB** cap is
  the binding limit. At ~0.8–1.1 KB (§2.1) there is ample headroom, but the
  peer list is the growing term (~30 B per peer id ⇒ 25 KB ≈ 800 peers).
  Delta-triggered updates keep it small; a very large swarm would need
  paged/indirect peer lists.
- There is **no minimum**, so `QDN_CHUNK_MIN_BYTES` is a QLive batching floor and
  a short final chunk is valid (see §1.2).

*Sources:* Qortal Core — `Service.java` (per-service `maxSize`),
`ArbitraryDataFile.java` (`MAX_FILE_SIZE`, `CHUNK_SIZE`); Qortal QDN docs —
`qdn-basics.md`, `qortal.dev/docs/q-apps`.

### 4.2 What QLive places on QDN

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

**To verify (Qortal docs / running node):** the size limits for the
**FILE/VIDEO** services (the doc states APP/IMAGE/JSON/MAIL/THUMBNAIL only),
whether nodes prune/expire resources and on what schedule, and the storage-cost
expectation for GB-scale archives. QLive assumes GB-scale resources are
acceptable because Q-Tube already stores VOD at this size — **confirm**.

---

## 5. Recommendations

1. **Publish archive chunks under `service: FILE`** and flush them toward 50 MB
   ~~(not the 10 MB floor)~~ — **implemented**: FILE has no per-service cap
   (bounded by `MAX_FILE_SIZE` = 2 GiB, enforced in `ArchivalPipeline`), and
   ceiling-flushing gives ~5× fewer QDN resources, publishes, and manifest
   entries at equal data volume. `min_chunk_bytes` remains the protocol floor /
   config guard, and the final chunk may be smaller.
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

- [ ] Actual QORT fee per QDN publish transaction? (The fee is size-proportional; measure the constant.)
- [ ] Does QDN update a resource in place or append a version per re-publish? (Docs say re-publishing the same name+service+identifier **overwrites**.)
- [x] Size limit for the archive-chunk service? **FILE has no per-service cap**, bounded by `MAX_FILE_SIZE` = 2 GiB. QLive publishes archive chunks as `service: FILE`.
- [ ] Size limits for **VIDEO/AUDIO/DOCUMENT** services (not confirmed in the sources checked).
- [ ] Any pruning/expiry policy for large (GB-scale) resources?
- [ ] Real on-chain tx size for a metadata publish?
- [ ] Measured QDN publish→retrievable latency (affects peer-list freshness).
- [x] Is `QDN_CHUNK_MIN_BYTES` a QDN minimum? **No** — QDN imposes no minimum; it is a QLive batching floor.

---

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-10-12 | Flush archive chunks toward the 50 MB ceiling, keep 10 MB as the protocol floor | The 10 MB floor made archives ~5× chunkier than the protocol allows; fewer chunks cut QDN resources, publishes, and manifest entries. **Implemented** in `ArchivalPipeline.add_chunk` (flush before a fragment would exceed the ceiling) |
| 2026-10-12 | Cost model is pay-per-publish-event; per-publish fee to verify | Live media never touches the chain; only < 1.2 KB metadata + the final archive do |
| 2026-10-12 | `QDN_CHUNK_MIN_BYTES` reclassified as a QLive **batching floor**, not a QDN limit | Qortal QDN enforces per-service **maximums** (APP 50 MB, IMAGE 10 MB, JSON 25 KB, MAIL 1 MB, THUMBNAIL 500 KB) and **no minimum**; short final chunks are therefore valid |
| 2026-10-12 | Added `FinalChunkPolicy` (`ALLOW_SHORT` default, `MERGE` opt-in) | Default matches QDN reality; `MERGE` serves deployments that impose their own floor (folds a sub-floor remainder into the previous chunk) |
| 2026-10-12 | Pin archive chunks to the **FILE** service; ceiling 50 MB, hard-bounded by `MAX_FILE_SIZE` (2 GiB) | FILE has no per-service cap and is a single file; 2 GiB is the binding limit. 50 MB keeps chunks in RAM with fine manifest/partial-retrieval granularity. Enforced in `ArchivalPipeline` |

---

*This document is a living artifact. Update it once QDN publish costs, tx size,
and retention behavior are measured against a running node.*
