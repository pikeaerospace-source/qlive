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

---

## Implementation

- `qlive/archival.py` — `ArchivalPipeline`, `QDNDataChunk`, `QTubeManifest`,
  `verify_integrity`.

*See [protocol.md](protocol.md) §7 for the full specification.*
