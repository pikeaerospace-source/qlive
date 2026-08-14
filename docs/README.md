# QLive Documentation

This directory will contain the formal protocol specification, design documents, and research notes for QLive.

---

## Planned Documents

| Document | Status | Description |
| --- | --- | --- |
| `protocol.md` | Draft | Formal protocol specification (chunk format, signaling schema, swarm protocol) |
| `monetization.md` | Draft | QORT token economy, monetization models, and incentive design |
| `architecture.md` | Planned | Detailed architecture and component design |
| `signaling-schema.md` | Planned | QDN signaling schema (stream metadata, peer lists, encryption keys) |
| `chunk-format.md` | Planned | CMAF/fMP4 ephemeral chunk format specification |
| `swarm-protocol.md` | Planned | Tree + mesh hybrid swarm membership and fallback logic |
| `buffer-design.md` | Planned | RAM sliding-window buffer semantics |
| `vod-pipeline.md` | Planned | Live → VOD archival pipeline design |
| `incentives.md` | Planned | Tit-for-tat and proof-of-relay incentive model |
| `research/` | Complete | Research notes — individual files (see Research Documents below) |

---

## Research Documents

Open research topics from [TODO.md](../TODO.md) → Phase 0 → Research Questions. Each document is a living TODO-style artifact with findings, test results, planning, and recommendations.

| Document | Topic |
| --- | --- |
| [`CHUNK-SIZE-TUNING.md`](CHUNK-SIZE-TUNING.md) | Optimal fragment duration (500ms vs 1s) — latency vs. overhead |
| [`BUFFER-SIZING.md`](BUFFER-SIZING.md) | Ideal sliding-window size (30s vs 60s) — resilience vs. RAM |
| [`ENCRYPTION-MODEL.md`](ENCRYPTION-MODEL.md) | Per-stream symmetric vs. per-viewer asymmetric keys; key rotation |
| [`BANDWIDTH-MEASUREMENT.md`](BANDWIDTH-MEASUREMENT.md) | Measuring peer bandwidth for tit-for-tat and proof-of-relay |
| [`NAT-TRAVERSAL.md`](NAT-TRAVERSAL.md) | NAT traversal strategy (STUN/TURN, hole punching, Reticulum) |
| [`RETICULUM-INTEGRATION.md`](RETICULUM-INTEGRATION.md) | Reticulum routing for peer discovery; latency vs. WebRTC |
| [`QDN-SIGNALING-FREQUENCY.md`](QDN-SIGNALING-FREQUENCY.md) | Swarm peer-list refresh cadence without chain bloat |
| [`QORTAL-CORE-API.md`](QORTAL-CORE-API.md) | Reusable Qortal Core endpoints (QDN, names, peers) |
| [`SWARM-SIMULATION.md`](SWARM-SIMULATION.md) | Discrete-event swarm simulation — fanout, mesh, retransmit, buffer, churn |
| [`THREAT-MODEL.md`](THREAT-MODEL.md) | Threat model (STRIDE + attack vectors) for live streaming |
| [`SECURITY-MODEL.md`](SECURITY-MODEL.md) | Sybil resistance, DoS resilience, receipt forgery, key distribution |
| [`ECONOMIC-MODELING.md`](ECONOMIC-MODELING.md) | Relay/streamer/viewer economics, proof-of-relay design, free-riders |

---

## Contributing to Docs

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines. Design documents should be written in Markdown and follow the project's style conventions.

---

*Documentation is a living artifact — update it as the design evolves.*