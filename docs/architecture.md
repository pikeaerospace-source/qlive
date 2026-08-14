# QLive Architecture

**Status:** Reference — mirrors the implemented components.

This document describes QLive's three-layer architecture and maps each layer
to its implementation. It complements the formal specification in
[protocol.md](protocol.md).

---

## Three Layers

```
┌─────────────────────────────────────────────────────────┐
│ 1. Signaling / Discovery (QDN — slow, permanent)         │
│    Stream metadata, publisher identity, peer lists, keys │
├─────────────────────────────────────────────────────────┤
│ 2. Ephemeral P2P Transport (RAM — fast, transient)       │
│    Tree push + mesh pull of signed, encrypted chunks     │
├─────────────────────────────────────────────────────────┤
│ 3. QDN Archival (VOD — on stream end)                    │
│    Aggregates live chunks into QDN data chunks           │
└─────────────────────────────────────────────────────────┘
```

---

## Component Map

| Layer | Concern | Python module | Web UI |
| --- | --- | --- | --- |
| Signaling | Stream metadata schema | `qlive/signaling.py` | `src/js/src/types.ts` |
| Signaling | Stream registry (QDN stand-in) | `qlive/signaling.py` | `src/js/src/data/api.ts` |
| Transport | Chunk format + signing | `qlive/chunk.py` | — |
| Transport | CMAF/fMP4 segmentation | `qlive/segmenter.py` | — |
| Transport | Delivery tree + mesh | `qlive/swarm.py` | — |
| Transport | Sliding-window buffer | `qlive/buffer.py` | — |
| Transport | Retransmission | `qlive/retransmit.py` | — |
| Transport | Adaptive bitrate | `qlive/adaptive.py` | — |
| Transport | Per-stream encryption | `qlive/encryption.py` | — |
| Archival | Live → VOD pipeline | `qlive/archival.py` | — |
| Incentives | Tit-for-tat | `qlive/incentives.py` | — |
| Incentives | Proof-of-relay | `qlive/proof.py` | — |
| Apps | Broadcaster / viewer | `qlive/broadcaster.py`, `viewer.py` | `src/js/src/pages/` |
| Tooling | Benchmarks & simulation | `qlive/benchmarks/`, `qlive/simulation.py` | — |

---

## Data Flow

1. **Broadcast:** the broadcaster segments media, encrypts (private streams),
   signs each chunk, and pushes it down the delivery tree.
2. **Watch:** a viewer receives chunks, verifies signatures, buffers them,
   detects gaps, and pulls missing chunks from mesh peers.
3. **Adapt:** the viewer adjusts bitrate based on buffer health.
4. **Archive:** expired chunks are aggregated into QDN data chunks; on stream
   end a Q-Tube manifest is generated.

---

## Current Status

- The Python reference implementation is complete and runs **fully offline**
  (in-memory registry, no QDN, no sockets) — 294 tests.
- The React + Vite Web UI (`src/js/`) mirrors the signaling schema and runs
  offline against a mock `Api`.
- Live QDN signaling and real P2P transport are **not yet wired** (network-gated).

---

*See [protocol.md](protocol.md) for the formal specification.*
