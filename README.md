# QLive

**Decentralized live streaming for the Qortal network.**

QLive is a real-time, peer-to-peer live streaming protocol built on top of Qortal's decentralized infrastructure. It delivers low-latency video to an unlimited audience without a single centralized server, CDN, or ingest point — while leaving **zero long-term disk footprint** on participating nodes.

> **The problem:** Q-Tube handles static video (VOD) beautifully by chunking and distributing files across the Qortal Data Network (QDN). But live streaming demands low latency, dynamic peer discovery, and transient data handling — constraints that traditional on-chain/QDN approaches cannot satisfy without bloating the blockchain or overloading node storage.

> **The solution:** QLive decouples **Signaling/Discovery** (handled on-chain via QDN) from **Data Transport** (handled via an ephemeral P2P mesh overlay running entirely in RAM).

---

## Table of Contents

- [Why QLive?](#why-qlive)
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
  - [1. Ephemeral Chunking Engine (CMAF / fMP4)](#1-ephemeral-chunking-engine-cmaf--fmp4)
  - [2. Dual-Layer Peer Swarm (Tree + Mesh Hybrid)](#2-dual-layer-peer-swarm-tree--mesh-hybrid)
  - [3. RAM-Only Sliding-Window Buffering](#3-ram-only-sliding-window-buffering)
  - [4. Automated Live → VOD Transition (Q-Tube Integration)](#4-automated-live--vod-transition-q-tube-integration)
- [Technical Constraints & Challenges](#technical-constraints--challenges)
- [Comparison: Traditional vs. Qortal Mesh Live](#comparison-traditional-vs-qortal-mesh-live)
- [Network Incentives & Free-Rider Mitigation](#network-incentives--free-rider-mitigation)
- [Getting Started](#getting-started)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why QLive?

Traditional live streaming is built on centralized infrastructure:

- **Ingest** requires RTMP servers (Twitch, YouTube).
- **Distribution** requires paid CDNs (Cloudflare, AWS CloudFront).
- **Storage** requires infinite server capacity.
- **Censorship** is a single point of failure — one domain block or shutdown kills the stream.

QLive flips this model. The broadcaster's node is the ingest point. The audience *is* the CDN. Storage is a rolling RAM buffer that never touches disk. And because routing happens over Qortal's peer network with encrypted swarms, there is no single point of failure or censorship.

**The network gets stronger as the viewer count grows.**

---

## Architecture Overview

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

**Two layers, one protocol:**

1. **QDN / Chain Layer (Signaling)** — Slow, permanent, authoritative. Publishes stream metadata, publisher identity, active swarm peer lists, and encryption keys. This is the *directory* for the stream.
2. **Ephemeral P2P Mesh (Transport)** — Fast, transient, in-RAM. Moves actual video fragments between peers in real time. This is the *highway* for the stream.
3. **QDN Archival (VOD Engine)** — The bridge between live and on-demand. Stitches expired live fragments into permanent QDN data chunks and publishes them as a Q-Tube video when the stream ends.

---

## Core Components

### 1. Ephemeral Chunking Engine (CMAF / fMP4)

- **Sub-Second Fragments:** The broadcaster's encoder produces ultra-short **Chunked Media Application Format (CMAF)** or fragmented MP4 (fMP4) slices (e.g., 500ms to 1s duration) for low-latency playback.
- **Cryptographic In-Flight Signing:** The broadcaster signs each chunk payload (`Sequence_ID`, `Timestamp`, `Data_Hash`) using their registered Qortal Name/Key pair. Viewer nodes verify signatures in real time to prevent injection attacks or corrupted streams.

### 2. Dual-Layer Peer Swarm (Tree + Mesh Hybrid)

A pure BitTorrent-style mesh introduces latency; a rigid tree breaks when a node leaves. QLive uses a hybrid:

- **Primary Delivery Tree (Low Latency):** High-capacity, high-uptime nodes form a primary distribution tree for push-based delivery directly from the broadcaster.
- **Secondary Local Swarm Mesh (Resilience):** Viewer nodes nearby in the network topology exchange missing fragments over WebRTC/Reticulum data channels. If a parent node in the primary tree drops, the client falls back to pulling missing sub-chunks from its local mesh buffer.

### 3. RAM-Only Sliding-Window Buffering

- Nodes participating in a live stream store video fragments strictly in a **rolling RAM cache** (e.g., keeping only the last 30–60 seconds of video in memory).
- Once a fragment moves out of the active live window, it is flushed from RAM — avoiding disk wear and storage bloat.

### 4. Automated Transition from Live to VOD (Q-Tube Integration)

As the live broadcast progresses, a background process on the streamer's node aggregates expired live chunks into standard **QDN Data Chunks** (e.g., 10MB–50MB blocks). When the live stream finishes:

1. The static archive is committed to QDN.
2. A Q-Tube manifest is published under the same Qortal Name.
3. The stream instantly becomes a permanent replayable video on Q-Tube — **without re-encoding**.

---

## Technical Constraints & Challenges

| Challenge | QLive's Answer |
| --- | --- |
| **Disk I/O & Storage Bloat** — Live streams produce gigabytes of ephemeral video; committing every fragment to permanent QDN storage would bloat the network. | RAM-only sliding-window buffering. Fragments live in memory for 30–60s, then are flushed. Only the *final* archive is committed to QDN. |
| **Blockchain State & Transaction Throughput** — Block times and ledger consensus are far too slow for real-time video sync. | Live fragment manifests are **never** registered on the main Qortal ledger. Only lightweight signaling metadata (stream info, peer lists, keys) touches the chain. |
| **Peer Churn & Network Instability** — Viewers join/leave unpredictably; a dropped relay must not freeze downstream viewers. | Dual-layer swarm (tree + mesh). If a primary-tree parent drops, clients pull missing fragments from the local mesh buffer. |

---

## Comparison: Traditional vs. Qortal Mesh Live

| Feature | Traditional Live (HLS / CDN) | Decentralized P2P Mesh (QLive) |
| --- | --- | --- |
| **Ingest Infrastructure** | Centralized Ingest (RTMP / Twitch / YouTube) | Direct Local Peer Broadcast |
| **Bandwidth Distribution** | Paid CDNs (Cloudflare, AWS CloudFront) | Distributed Peer-to-Peer Relay Swarm |
| **Node Storage Impact** | Infinite server storage required | Zero long-term disk impact (RAM-only rolling buffer) |
| **Censorship Resistance** | Single point of shutdown or domain block | Fully resistant via Qortal peer routing & encrypted swarms |
| **Viewer Scalability** | Costs increase linearly with viewer count | **Network gets stronger as viewer count grows** |

---

## Network Incentives & Free-Rider Mitigation

To ensure peers actually relay video traffic rather than just leeching bandwidth:

- **Tit-for-Tat Data Swapping:** Viewer nodes prioritize sending fragments to peers that contribute bandwidth back to the swarm.
- **Proof-of-Relay (Minting / Reputation Integration):** Nodes actively relaying live streams can collect signed bandwidth receipts from peer nodes. These micro-proofs could feed into Qortal's node reputation system or minting weight calculations to reward infrastructure contributors.

---

## Getting Started

> **Status:** Active development. A Python reference implementation of the core protocol (chunking, buffering, swarm, signaling, archival, incentives) and a React web UI are in place — both run fully offline against mock data. Live Qortal network integration (QDN signaling, real P2P transport) is not yet wired up. See [TODO.md](TODO.md) for the roadmap.

### Prerequisites

- Python 3.10+ (reference implementation)
- Node.js 20+ (web UI)
- FFmpeg (broadcaster encoder — optional for offline work)
- A Qortal Core node (QDN signaling — not yet required)

### Reference implementation (Python)

```bash
cd src/python
pip install -e ".[dev]"
pytest                       # 275 tests
python -m qlive.benchmarks   # offline benchmarks
```

### Web UI (React + Vite)

```bash
cd src/js
npm install
npm run dev                  # http://localhost:5173 (offline, mock data)
```

### CLI (illustrative)

```bash
# Start a broadcaster (requires a Qortal node + FFmpeg)
qlive broadcast --name "my-qortal-name" --source "rtmp://localhost/live"

# Watch a stream
qlive watch --stream "qortal://my-qortal-name/live"
```

> ⚠️ The CLI and transport are wired to in-memory/mock components; live QDN signaling and real P2P transport are pending.

---

## Roadmap

See [TODO.md](TODO.md) for the full, living roadmap. High-level milestones:

1. **Phase 0 — Research & Spec** — Protocol design, chunk format, signaling schema.
2. **Phase 1 — Core Transport** — Ephemeral chunking engine + RAM sliding-window buffer.
3. **Phase 2 — Swarm & Discovery** — Dual-layer peer swarm + QDN signaling integration.
4. **Phase 3 — VOD Bridge** — Live → Q-Tube archival pipeline.
5. **Phase 4 — Incentives** — Tit-for-tat, proof-of-relay, reputation integration.
6. **Phase 5 — UX & Tooling** — Broadcaster app, viewer app, Q-Tube integration.

---

## Contributing

Contributions are welcome across:

- Protocol design & specification
- Reference implementation (Python / React / WebRTC / Reticulum)
- Qortal Core integration
- Documentation & testing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, [SECURITY.md](SECURITY.md) for security reporting, and [TODO.md](TODO.md) for open tasks.

---

## License

Licensed under the [MIT License](LICENSE.md). Copyright (c) 2026 Mike Sharkey <mike@pikeaero.com>.

---

*QLive — live streaming that belongs to the network, not the platform.*