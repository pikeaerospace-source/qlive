# Live → VOD Archival Pipeline

**Status:** Reference — mirrors `qlive/archival.py` and `protocol.md` §7.

A background process aggregates expired live chunks into QDN data chunks and,
on stream end, publishes a Q-Tube manifest.

---

## Stages

1. **Aggregation** — expired chunks are buffered and concatenated into QDN
   data chunks (10–50 MB).
2. **Hash chain** — each QDN chunk links to the previous chunk's hash for
   integrity verification.
3. **Manifest** — on finalize, a `QTubeManifest` is generated with chunk
   hashes, total size, fragment count, and duration.
4. **Publish** — the manifest is published under the broadcaster's Qortal Name.

## Interrupted Streams

A partial archive is marked `isPartial`; viewers can still watch what was
recorded.

## Viewer Replay UX

The archive reuses the original live fragments verbatim — playback is **not
re-encoded** — so a stream's replay is only a matter of publishing (or pointing
at) the archived QDN resource.

The Web UI derives a single viewer-facing replay state per stream
(`src/js/src/data/archive.ts`):

| State | Condition | UI |
| --- | --- | --- |
| `none` | `live` / `announced`, or no archive metadata | live player only |
| `archiving` | `ended` / `interrupted`, or archive `status: pending` | "Archiving…" notice, no replay link |
| `ready` | archive `status: archived` | "Replay available" + **Watch replay** link, duration/size/fragment metrics |
| `partial` | archive `status: partial` | as `ready`, plus a warning that the replay is incomplete |

Stream metadata points at the archive (`archive.qdnResourceId` /
`archive.qtubeManifestId`); playback resolves to
`/arbitrary/VIDEO/<publisher>/<qdnResourceId>`, i.e. the platform player fetches
the same CMAF fragments that were relayed live. A finished stream moves
`archiving → ready` with no transcoding step, and `interrupted` streams land on
`partial` so viewers know the recording has gaps.

---

## Implementation

- `qlive/archival.py` — `ArchivalPipeline`, `QDNDataChunk`, `QTubeManifest`,
  `verify_integrity`.

*See [protocol.md](protocol.md) §7 for the full specification.*
