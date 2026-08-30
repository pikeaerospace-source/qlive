# QLive Protocol Specification v0.1.0 (Draft)

**Status:** Draft — subject to change during Phase 0 research.

This document specifies the QLive protocol for decentralized live streaming on the Qortal network. It defines the ephemeral chunk format, QDN signaling schema, swarm membership protocol, RAM buffer semantics, and the Live → VOD archival pipeline.

---

## 1. Overview

QLive decouples **Signaling/Discovery** (handled on-chain via QDN) from **Data Transport** (handled via an ephemeral P2P mesh overlay running in RAM).

```
┌─────────────────────────────────────────────────────────┐
│              QDN / Chain Layer (Signaling)              │
│  - Stream Metadata & Publisher Identity                 │
│  - Active Swarm Peer List & Encryption Keys             │
└───────────────────────────┬─────────────────────────────┘
                            │ (Discovery)
                            ▼
┌─────────────────────────────────────────────────────────┐
│             Ephemeral P2P Mesh (RAM Transport)          │
│  Publisher  ───>  Node A (Relay)  ───>  Node C (Viewer) │
│     │                                        ▲          │
│     └───────────>  Node B (Relay)  ──────────┘          │
└───────────────────────────┬─────────────────────────────┘
                            │ (Sliding-Window Archive)
                            ▼
┌─────────────────────────────────────────────────────────┐
│               QDN Archival (VOD Engine)                 │
│  - Stitches live chunks into standard QDN Data Chunks   │
│  - Converts completed Live Stream into a Q-Tube Video   │
└─────────────────────────────────────────────────────────┘
```

### 1.1 Design Principles

1. **Zero long-term disk footprint** — live fragments live in RAM only
2. **No blockchain bloat** — live fragment manifests never touch the Qortal ledger
3. **Low latency** — sub-second fragment delivery via push-based tree
4. **Resilience** — mesh fallback on tree parent drop
5. **Censorship resistance** — no single point of failure
6. **Self-scaling** — network capacity grows with viewer count

---

## 2. Terminology

| Term | Definition |
| --- | --- |
| **Broadcaster** | The node producing the live stream, identified by a Qortal Name |
| **Viewer** | A node consuming the live stream |
| **Relay** | A node forwarding live fragments to downstream peers |
| **Fragment** | A single CMAF/fMP4 media slice (500ms–1s duration) |
| **Chunk** | A signed fragment payload with metadata header |
| **Swarm** | The set of nodes participating in a stream's distribution |
| **Primary Tree** | Push-based delivery hierarchy from the broadcaster |
| **Local Mesh** | Pull-based fragment exchange among nearby viewers |
| **Sliding Window** | The rolling RAM buffer holding recent fragments (30–60s) |
| **QDN** | Qortal Data Network — the decentralized storage layer |
| **Qortal Name** | The registered identity of a node on Qortal |

---

## 3. Ephemeral Chunk Format

### 3.1 Chunk Structure

Each chunk is a self-contained, signed unit of media data:

```
┌──────────────────────────────────────────────────────┐
│                    Chunk Header                      │
├──────────────────────────────────────────────────────┤
│  Magic:        "QLIV" (4 bytes)                      │
│  Version:      uint8 (currently 1)                   │
│  Stream ID:    32 bytes (SHA-256 of stream metadata) │
│  Sequence ID:  uint64 (monotonic per stream)         │
│  Timestamp:    uint64 (milliseconds since epoch)     │
│  Duration:     uint16 (milliseconds)                 │
│  Payload Size: uint32 (bytes)                        │
│  Payload Hash: 32 bytes (SHA-256 of payload)         │
│  Signature:    64 bytes (Ed25519)                    │
├──────────────────────────────────────────────────────┤
│                    Chunk Payload                     │
├──────────────────────────────────────────────────────┤
│  CMAF/fMP4 media data (video/audio segments)         │
└──────────────────────────────────────────────────────┘
```

### 3.2 Header Fields

| Field | Size | Description |
| --- | --- | --- |
| `Magic` | 4 bytes | Constant `0x51 0x4C 0x49 0x56` ("QLIV") |
| `Version` | 1 byte | Protocol version (currently `1`) |
| `Stream ID` | 32 bytes | SHA-256 hash of the stream metadata document |
| `Sequence ID` | 8 bytes | Monotonic counter, starts at 1, increments per fragment |
| `Timestamp` | 8 bytes | Unix epoch milliseconds when the fragment was captured |
| `Duration` | 2 bytes | Fragment duration in milliseconds (500–1000) |
| `Payload Size` | 4 bytes | Size of the payload in bytes |
| `Payload Hash` | 32 bytes | SHA-256 of the payload bytes |
| `Signature` | 64 bytes | Ed25519 signature over the 91-byte header (the fields preceding it) |

### 3.3 Signing

- The broadcaster signs each chunk with their Qortal Name's Ed25519 key pair
- The signature covers the header: `Magic || Version || Stream ID || Sequence ID || Timestamp || Duration || Payload Size || Payload Hash`. The header embeds the SHA-256 `payload_hash`, so the signature binds the payload while keeping sign/verify cost constant regardless of bitrate (see [ENCRYPTION-MODEL.md](ENCRYPTION-MODEL.md))
- Viewer/relay nodes MUST verify the signature before accepting a chunk
- Signature verification uses the broadcaster's public key, resolved from their Qortal Name

### 3.4 Fragment Duration

- Default: **1000ms** (1 second)
- Minimum: **500ms**
- Maximum: **2000ms**
- The broadcaster MAY adjust duration based on network conditions
- Duration is communicated in the stream metadata

---

## 4. QDN Signaling Schema

### 4.1 Stream Metadata Document

Published to QDN under the broadcaster's Qortal Name. This is the authoritative source of stream information.

```json
{
  "type": "qlive-stream",
  "version": 1,
  "streamId": "sha256-hash-of-this-document",
  "publisher": "qortal-name",
  "title": "My Live Stream",
  "description": "Optional description",
  "category": "gaming|music|tech|other",
  "startedAt": 1734134400000,
  "status": "live|ended|archived",
  "fragmentDurationMs": 1000,
  "codec": {
    "video": "h264|h265|av1|vp9",
    "audio": "aac|opus",
    "container": "cmaf|fmp4"
  },
  "resolution": {
    "width": 1920,
    "height": 1080,
    "fps": 30
  },
  "bitrate": {
    "video": 4500000,
    "audio": 128000
  },
  "encryption": {
    "enabled": false,
    "keyId": null
  },
  "swarm": {
    "primaryTree": ["node-id-1", "node-id-2"],
    "meshPeers": ["node-id-3", "node-id-4"]
  },
  "archive": {
    "status": "pending|in-progress|complete",
    "qdnResourceId": null,
    "qtubeManifestId": null
  }
}
```

### 4.2 Stream Lifecycle

```
announced → live → ended → archived
                ↘ interrupted → partial-archive
```

| State | Description |
| --- | --- |
| `announced` | Stream metadata published, waiting to start |
| `live` | Broadcaster is producing fragments |
| `ended` | Broadcaster stopped, archive in progress |
| `archived` | VOD committed to QDN, Q-Tube manifest published |
| `interrupted` | Broadcaster node died unexpectedly |

### 4.3 QDN Update Cadence

| Update | Frequency | Purpose |
| --- | --- | --- |
| Stream metadata | On state change | Announce, start, end, archive |
| Swarm peer list | Every 30–60s | Keep peer lists fresh |
| Encryption key rotation | Every 5–10 min | Key rotation for private streams |

---

## 5. Swarm Protocol

### 5.1 Dual-Layer Architecture

```
        ┌─────────────┐
        │ Broadcaster │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  Tree Node  │  ← Primary Delivery Tree (push)
        │   (Relay)   │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  Tree Node  │
        │   (Relay)   │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Viewer    │  ← Local Mesh (pull fallback)
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Viewer    │
        └─────────────┘
```

### 5.2 Primary Delivery Tree

- **Node selection:** High-capacity, high-uptime nodes are selected as tree nodes
- **Push-based:** Fragments are pushed downstream from the broadcaster
- **Fan-out:** Each tree node serves up to N downstream nodes (default: 8)
- **Tree depth:** Maximum depth of 5 hops from broadcaster
- **Rebalancing:** Tree is rebalanced when nodes join/leave

### 5.3 Local Mesh

- **Membership:** Nearby viewers (by network topology) form a mesh
- **Pull-based:** Missing fragments are requested from mesh peers
- **Fallback:** If a tree parent drops, the viewer pulls missing fragments from the mesh
- **Mesh size:** 4–16 peers per viewer

### 5.4 Peer Health

| Metric | Threshold | Action |
| --- | --- | --- |
| Latency | > 500ms | Demote from tree, use mesh |
| Packet loss | > 5% | Request retransmission |
| Uptime | < 60s | Not eligible for tree node |
| Bandwidth | < 1 Mbps | Not eligible for relay |

### 5.5 Fragment Flow

1. Broadcaster produces fragment → signs → pushes to tree children
2. Tree nodes verify signature → buffer in RAM → push downstream
3. Viewer receives fragment → verifies → buffers → plays
4. If gap detected → request missing fragment from mesh peers
5. If tree parent drops → switch to mesh pull mode

---

## 6. RAM Sliding-Window Buffer

### 6.1 Semantics

- Each node maintains a rolling buffer of the last **30–60 seconds** of fragments
- Buffer is strictly in-memory — **never written to disk**
- Fragments older than the window are evicted

### 6.2 Buffer Parameters

| Parameter | Default | Range |
| --- | --- | --- |
| Window size | 45s | 30–60s |
| Max memory | 256 MB | Configurable |
| Eviction | Oldest-first | FIFO |

### 6.3 Buffer States

| State | Description |
| --- | --- |
| `filling` | Buffer below target, waiting for data |
| `healthy` | Buffer at target, normal playback |
| `stalling` | Buffer underflow, playback paused |
| `overflow` | Buffer full, evicting oldest |

### 6.4 Adaptive Behavior

- On `stalling`: request retransmission from mesh, reduce playback quality if available
- On `overflow`: evict oldest fragments, optionally reduce buffer size
- On `healthy`: maintain current settings

---

## 7. Live → VOD Archival Pipeline

### 7.1 Aggregation

- The broadcaster's node aggregates expired fragments into **QDN Data Chunks**
- Chunk size: **10MB–50MB**
- Fragments are concatenated in sequence order
- Each QDN chunk is hashed and linked (hash chain)

### 7.2 Commit

When the stream ends:

1. Final QDN data chunks are committed to QDN
2. A Q-Tube manifest is generated referencing the chunks
3. The manifest is published under the broadcaster's Qortal Name
4. Stream metadata is updated to `archived`

### 7.3 Interrupted Streams

- If the broadcaster dies mid-stream, any node with the full fragment history MAY commit the archive
- Partial archives are marked as such in the metadata
- Viewers can still watch the partial archive

---

## 8. Security

### 8.1 Threat Model

| Threat | Mitigation |
| --- | --- |
| Chunk injection | Ed25519 signature verification on every chunk |
| Stream spoofing | Qortal Name identity binding |
| DoS / flooding | Rate limiting, tit-for-tat, reputation |
| Free-riding | Tit-for-tat data swapping |
| Eavesdropping | Per-stream encryption (optional) |
| Sybil attacks | Qortal Name identity, reputation |
| Storage bloat | RAM-only buffer, strict eviction |

### 8.2 Encryption (Private Streams)

- Streams MAY be encrypted with a symmetric key (AES-256-GCM)
- The key is distributed via QDN signaling, encrypted to authorized viewers' public keys
- Keys rotate every 5–10 minutes
- Each chunk's payload is encrypted; the header remains plaintext for routing

---

## 9. Incentives

### 9.1 Tit-for-Tat

- Each node tracks bandwidth contributed to and received from each peer
- Nodes prioritize sending fragments to peers that contribute bandwidth back
- Free-riders are deprioritized and eventually disconnected

### 9.2 Proof-of-Relay

- Relay nodes collect signed bandwidth receipts from downstream peers
- Receipts include: relay node ID, downstream node ID, bytes relayed, timestamp
- Receipts MAY feed into Qortal's reputation/minting systems (future work)

---

## 10. Protocol Constants

| Constant | Value |
| --- | --- |
| `MAGIC` | `0x514C4956` ("QLIV") |
| `VERSION` | `1` |
| `DEFAULT_FRAGMENT_MS` | `1000` |
| `MIN_FRAGMENT_MS` | `500` |
| `MAX_FRAGMENT_MS` | `2000` |
| `DEFAULT_BUFFER_SECONDS` | `45` |
| `MIN_BUFFER_SECONDS` | `30` |
| `MAX_BUFFER_SECONDS` | `60` |
| `MAX_TREE_DEPTH` | `5` |
| `DEFAULT_TREE_FANOUT` | `8` |
| `MESH_PEERS_MIN` | `4` |
| `MESH_PEERS_MAX` | `16` |
| `QDN_CHUNK_MIN_BYTES` | `10 * 1024 * 1024` |
| `QDN_CHUNK_MAX_BYTES` | `50 * 1024 * 1024` |
| `SIGNATURE_BYTES` | `64` (Ed25519) |
| `HASH_BYTES` | `32` (SHA-256) |

---

## 11. Open Questions

This spec is a draft. Open questions that need resolution:

1. **Transport:** WebRTC vs. Reticulum vs. both?
2. **NAT traversal:** STUN/TURN, hole punching, or Reticulum transport?
3. **Adaptive bitrate:** Multi-bitrate ladders in v1?
4. **Archive ownership:** Broadcaster-only or any node with full history?
5. **Encryption model:** Per-stream symmetric vs. per-viewer asymmetric?
6. **Latency target:** Sub-1s (WebRTC-style) vs. 2–5s (low-latency HLS)?

See [TODO.md](../TODO.md) → **Open Design Questions** for the full list.

---

*This specification is a living document. Update it as the design evolves.*