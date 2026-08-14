# QDN Signaling Schema

**Status:** Reference — mirrors `qlive/signaling.py` and `protocol.md` §4.

The signaling layer publishes lightweight stream metadata to QDN. It never
carries live video data.

---

## Stream Metadata Document

Serialized as JSON with `type: "qlive-stream"`. Fields:

| Field | Type | Description |
| --- | --- | --- |
| `version` | int | Schema version (1) |
| `publisher` | string | Broadcaster's Qortal Name |
| `title` | string | Stream title |
| `description` | string | Optional description |
| `category` | string | Free-form category |
| `startedAt` | int | Unix epoch ms |
| `status` | enum | `announced` / `live` / `ended` / `archived` / `interrupted` |
| `fragmentDurationMs` | int | Fragment duration |
| `codec` | object | `{ video, audio, container }` |
| `resolution` | object | `{ width, height, fps }` |
| `bitrate` | object | `{ video, audio }` (bps) |
| `renditions` | int[] | Advertised bitrate ladder (kbps) |
| `encryption` | object | `{ enabled, keyId }` |
| `swarm` | object | `{ primaryTree[], meshPeers[] }` |
| `archive` | object | `{ status, qdnResourceId, qtubeManifestId }` |

The **stream ID** is the SHA-256 of the serialized metadata document.

---

## Lifecycle

`announced → live → ended → archived` (or `interrupted` on abnormal end).

---

## Update Cadence

| Update | Frequency |
| --- | --- |
| Stream metadata | On state change only |
| Swarm peer list | Delta-triggered, 30–60 s cap |
| Key rotation | 5–10 min |

See [QDN-SIGNALING-FREQUENCY.md](QDN-SIGNALING-FREQUENCY.md) for the rationale.

---

## Implementation

- `qlive/signaling.py` — `StreamMetadata`, `StreamRegistry` (in-memory QDN stand-in).
- `src/js/src/types.ts` — the TypeScript mirror of this schema.

*See [protocol.md](protocol.md) §4 for the full specification.*
