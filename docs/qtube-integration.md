# Q-Tube Integration — Manifest Mapping

**Status:** Draft — Q-Tube's authoritative manifest schema is not yet confirmed
(coordination pending; see [TODO-QTUBE.md](../TODO-QTUBE.md)). This document
records QLive's emitted schema, a proposed field-by-field mapping, and the
invariants the compatibility test suite enforces. Update it once the Q-Tube
team confirms their format.

---

## 1. What QLive Emits

On finalize, `qlive/archival.py` produces a `QTubeManifest` that serializes via
`to_dict()` to a JSON object. It is published as a QDN `Service.JSON` document
under the broadcaster's Qortal Name.

```json
{
  "type": "qtube-video",
  "version": 1,
  "streamId": "<64-char hex of the 32-byte stream id>",
  "publisher": "alice",
  "title": "My Live Stream",
  "description": "",
  "category": "other",
  "startedAt": 1700000000000,
  "endedAt": 1700003600000,
  "chunkHashes": ["<sha256 hex>", "…"],
  "totalSize": 104857600,
  "fragmentCount": 3600,
  "durationMs": 3600000,
  "codec": "h264",
  "resolution": "1920x1080",
  "fps": 30,
  "isPartial": false
}
```

Field source: `QTubeManifest` (`src/python/qlive/archival.py`), schema documented
in [vod-pipeline.md](vod-pipeline.md) and [protocol.md](protocol.md) §7.

---

## 2. Field Mapping

| # | QLive field | Type | Required for Q-Tube | Proposed Q-Tube field | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `type` | `"qtube-video"` | ✅ | `type` | Discriminator; Q-Tube should gate on this value. |
| 2 | `version` | `1` (int) | ✅ | `version` | Schema version — bump on breaking change. |
| 3 | `streamId` | string (hex) | ✅ | `streamId` | Stable identity of the source live stream. |
| 4 | `publisher` | string | ✅ | `publisher` / `owner` | Qortal Name; may need to match Q-Tube's ownership field. |
| 5 | `title` | string | ✅ | `title` | Display title. |
| 6 | `description` | string | ⬜ optional | `description` | May be merged into Q-Tube's metadata block. |
| 7 | `category` | string | ⬜ optional | `category` | Q-Tube's taxonomy may use ids/enums. |
| 8 | `startedAt` | int (epoch ms) | ⬜ optional | `created` / `startedAt` | Unit (ms vs s) must be confirmed. |
| 9 | `endedAt` | int (epoch ms) | ⬜ optional | `endedAt` | |
| 10 | `chunkHashes` | string[] | ✅ | `chunkHashes` / `chunks[].hash` | Integrity list; Q-Tube may prefer per-chunk objects. |
| 11 | `totalSize` | int (bytes) | ⬜ optional | `totalSize` | |
| 12 | `fragmentCount` | int | ⬜ optional | `fragmentCount` | Live fragment (CMAF chunk) count, *not* QDN chunk count. |
| 13 | `durationMs` | int | ⬜ optional | `durationMs` | |
| 14 | `codec` | string | ⬜ optional | `codec` | Currently `"h264"`. |
| 15 | `resolution` | string `"WxH"` | ⬜ optional | `resolution` | Q-Tube may prefer `{width, height}`. |
| 16 | `fps` | int | ⬜ optional | `fps` | |
| 17 | `isPartial` | bool | ✅ | `isPartial` / `partial` | Distinguishes a full archive from an interrupted one. |

✅ = required for a replayable video; ⬜ = QLive provides it, Q-Tube may or may
not consume it.

---

## 3. Chunked Video (Multiple QDN Resources)

QLive archives a stream as a sequence of **QDN data chunks** (10–50 MB each),
linked in a hash chain (`QDNDataChunk`), each holding concatenated live
fragments. The manifest references them by `chunkHashes`.

Open mapping questions for Q-Tube:

- Does Q-Tube ingest a video as **one QDN resource per chunk** (streaming a
  playlist), or as a **single stitched resource**?
- If per-chunk, what identifier does Q-Tube expect for each chunk — the hash,
  a QDN resource name, or an index?
- How does Q-Tube address the manifest relative to its chunks (same Qortal Name
  + identifier prefix, or an embedded list of QDN names)?

QLive's playback path today resolves a replay to
`/arbitrary/VIDEO/<publisher>/<qdnResourceId>` (see
[vod-pipeline.md](vod-pipeline.md) §Viewer Replay UX), i.e. the platform player
fetches the archived fragments without re-encoding. The mapping must preserve
that invariant: **no re-encode, fragments served verbatim.**

---

## 4. Naming & Envelope

- QLive's live-stream signaling uses the identifier prefix `QLIVE_STREAM_<id>`
  (see [signaling-schema.md](signaling-schema.md)).
- The **archive manifest** should get its own identifier convention so it is
  distinguishable from the live signaling doc — proposed:
  `QLIVE_MANIFEST_<streamId>` (to be confirmed with Q-Tube; must not collide
  with the live `QLIVE_STREAM_` prefix).
- The envelope is a standard QDN `Service.JSON` document carrying
  `metadata.title/description/category` alongside the manifest body, matching
  how live stream metadata is published.

---

## 5. Compatibility Test Suite

`tests/python/test_qtube_compat.py` validates a representative manifest against
the invariants above — a fixture stands in for Q-Tube's reader while the real
schema is unconfirmed. It asserts:

1. The `type`/`version` discriminator is correct.
2. `streamId` is a 64-char lowercase hex string.
3. `chunkHashes` are lowercase SHA-256 hex (64 chars) and non-empty.
4. Timestamps are epoch-ms and `endedAt >= startedAt`.
5. Booleans/numerics have the expected JSON types (not strings).
6. `isPartial` correctly flags an interrupted archive.

When Q-Tube's schema lands, replace the fixture with their published schema and
keep these invariants as the cross-check.

---

## 6. Open Questions (for the Q-Tube team)

1. What is Q-Tube's authoritative manifest schema/version to target?
2. Required vs optional fields — which of QLive's optional fields must be
   present?
3. How does Q-Tube handle chunked video (multiple QDN resources)?
4. Identifier/envelope convention for the manifest document.
5. Timestamp unit (epoch ms vs s) and category taxonomy.
6. Does Q-Tube re-fetch by hash for integrity, or trust the publisher?

---

*See [TODO-QTUBE.md](../TODO-QTUBE.md) → Manifest Format Compatibility for the
tracking tasks.*