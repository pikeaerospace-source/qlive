# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Initial project scaffolding
  - `README.md` — project overview, architecture, and roadmap
  - `TODO.md` — phased task tracking, open design questions, milestones
  - `LICENSE.md` — MIT License
  - `CONTRIBUTING.md` — contribution guidelines
  - `SECURITY.md` — security policy and vulnerability reporting
  - `AUTHORS.md` — contributor acknowledgments
  - `.gitignore` — Python, JavaScript/Node.js, Java, and QLive-specific ignores
  - `.editorconfig` — cross-editor style consistency
  - `.gitattributes` — git line-ending and diff settings
  - `docs/` — documentation directory placeholder
- Project structure and tooling
  - `src/python/` — Python package with `pyproject.toml`, CLI skeleton, and package init
  - `src/js/` — TypeScript project with `package.json`, `tsconfig.json`, and entry point
  - `src/java/` — Maven project with `pom.xml` and main class skeleton
  - `tests/` — test suite directory structure
  - `.github/workflows/ci.yml` — CI pipeline for Python, JavaScript, and Java

### Design
- Security & simulation research
  - `docs/SWARM-SIMULATION.md` — discrete-event swarm simulation findings (fanout, mesh, retransmit, buffer, churn, free-riders)
  - `docs/THREAT-MODEL.md` — STRIDE threat model and attack vectors (chunk injection, swarm manipulation, economic attacks)
  - `docs/SECURITY-MODEL.md` — sybil resistance, DoS resilience, receipt-forgery analysis, key distribution
- Q-Stream architectural blueprint
  - QDN/Chain signaling layer
  - Ephemeral P2P mesh transport layer
  - QDN archival (VOD) layer
- Ephemeral chunking engine (CMAF/fMP4) with cryptographic in-flight signing
- Dual-layer peer swarm (tree + mesh hybrid)
- RAM-only sliding-window buffering
- Automated Live → VOD transition (Q-Tube integration)
- Tit-for-tat data swapping and proof-of-relay incentive model
- `docs/protocol.md` — formal protocol specification v0.1.0 (draft)
  - Ephemeral chunk format (header fields, signing, fragment duration)
  - QDN signaling schema (stream metadata, lifecycle, update cadence)
  - Swarm protocol (dual-layer tree + mesh, peer health, fragment flow)
  - RAM sliding-window buffer semantics
  - Live → VOD archival pipeline
  - Security threat model and encryption
  - Incentives (tit-for-tat, proof-of-relay)
  - Protocol constants

### Implemented
- `qlive/chunk.py` — ephemeral chunk format implementation
  - Binary chunk serialization/deserialization (155-byte header + payload)
  - Ed25519 chunk signing and verification
  - Payload hash validation (SHA-256)
  - Fragment duration validation (500–2000ms)
  - Stream ID validation (32 bytes)
- `tests/python/test_chunk.py` — 24 tests covering chunk creation, signing, verification, serialization, and error handling (98% coverage on chunk module)
- `qlive/buffer.py` — RAM sliding-window buffer implementation
  - In-memory ordered buffer keyed by sequence ID
  - Oldest-first eviction based on time window (30–60s)
  - Memory limit enforcement (default 256 MB)
  - Sequence gap detection and tracking
  - Buffer health states (filling, healthy, stalling)
  - Fill ratio monitoring
- `tests/python/test_buffer.py` — 24 tests covering buffer init, add, eviction, retrieval, and stats (98% coverage on buffer module)
- `qlive/segmenter.py` — FFmpeg-based CMAF/fMP4 segmenter
  - Configurable fragment duration (500–2000ms)
  - Zero-latency H.264/AAC encoding
  - Async segment streaming via `segments()` iterator
  - Lifecycle state management (idle, starting, running, stopping, stopped, error)
  - Graceful process termination
- `tests/python/test_segmenter.py` — 18 tests covering config, command building, start/stop lifecycle, and segment streaming (96% coverage on segmenter module)
- `qlive/retransmit.py` — chunk retransmission protocol
  - Request lifecycle states (pending, in-flight, complete, failed, timeout)
  - Request deduplication
  - Timeout-based retry with configurable max attempts
  - Chunk recovery tracking
  - Success rate statistics
- `tests/python/test_retransmit.py` — 23 tests covering request lifecycle, chunk handling, timeouts, and statistics (99% coverage on retransmit module)
- `qlive/adaptive.py` — adaptive bitrate control
  - Bitrate ladder with upgrade/downgrade logic
  - Hysteresis-based control to avoid oscillation
  - Cooldown periods for upgrades and downgrades
  - Buffer health-based bitrate selection
- `tests/python/test_adaptive.py` — 23 tests covering bitrate ladder, controller evaluation, and full adaptive cycles (100% coverage on adaptive module)
- `qlive/swarm.py` — dual-layer peer swarm
  - Primary delivery tree with capacity-based node selection
  - Secondary local mesh for resilience
  - Tree → mesh fallback on parent drop
  - Peer health monitoring and eligibility
  - Delivery path and downstream tracking
  - Swarm membership churn handling
- `tests/python/test_swarm.py` — 31 tests covering peer health, tree operations, swarm management, and fallback (93% coverage on swarm module)
- `qlive/signaling.py` — QDN signaling integration
  - Stream metadata schema (codec, resolution, bitrate, encryption, swarm, archive)
  - Stream lifecycle states (announced, live, ended, archived, interrupted)
  - Stream discovery by publisher and status
  - Swarm peer list publication/refresh
  - Archive status tracking
- `tests/python/test_signaling.py` — 22 tests covering metadata serialization, stream registry, and lifecycle management (100% coverage on signaling module)
- `docs/monetization.md` — QORT token economy design v0.2.0
  - On-chain signaling vs. off-chain ephemeral data costs
  - Monetization models (tips, PPV, micro-subscriptions)
  - Proof-of-relay bandwidth incentives
  - QORT burn vs. transfer models
  - Streamer revenue split (80/15/5)
  - Creator economy tiers
  - Economic attack vectors and mitigations
  - Dispute resolution framework
  - Minimum viable economics
  - Reputation-based pricing
- `qlive/archival.py` — Live → VOD archival pipeline
  - QDN data chunk creation (10MB–50MB blocks)
  - Hash chain integrity verification
  - Q-Tube manifest generation
  - Partial archive support (interrupted streams)
  - Automatic flush on stream end
- `tests/python/test_archival.py` — 16 tests covering QDN chunk hashing, manifest generation, pipeline operations, and integrity verification (98% coverage on archival module)
- `qlive/incentives.py` — tit-for-tat data swapping
  - Per-peer bandwidth contribution tracking
  - Contribution classification (contributing, neutral, free-rider)
  - Priority-based chunk delivery ordering
  - Free-rider detection with warning escalation
  - Inactivity timeout detection
- `tests/python/test_incentives.py` — 28 tests covering bandwidth accounting, contribution classification, free-rider detection, and prioritization (100% coverage on incentives module)
- `qlive/proof.py` — proof-of-relay bandwidth receipts
  - Signed bandwidth receipt format (Ed25519)
  - Receipt lifecycle (pending, verified, redeemed, rejected)
  - QORT calculation based on bytes relayed
  - Dispute window before redemption (24h default)
  - Per-relay-node earnings tracking
- `tests/python/test_proof.py` — 19 tests covering receipt signing, verification, redemption, and earnings (100% coverage on proof module)
- `qlive/broadcaster.py` — broadcaster application
  - Stream lifecycle management (idle, starting, live, stopping, stopped, error)
  - FFmpeg segmenter integration
  - Chunk signing and distribution
  - Automatic VOD archival
  - QDN signaling integration
  - Statistics tracking
- `tests/python/test_broadcaster.py` — 12 tests covering config, lifecycle, segment processing, and run loop (95% coverage on broadcaster module)
- `qlive/viewer.py` — viewer application
  - Stream discovery and connection
  - Chunk reception and buffering
  - Sequence gap detection and retransmission
  - Buffer health monitoring and stall recovery
  - Adaptive bitrate control
- `tests/python/test_viewer.py` — 17 tests covering connection, chunk reception, gap handling, retransmission, and buffer health (98% coverage on viewer module)
- `qlive/benchmarks/` — local, offline benchmark framework (no network/QDN/FFmpeg required)
  - `runner.py` — timing primitives (`best_time`) and result reporting (`Result`, `format_results`)
  - `chunk_bench.py` — chunk overhead ratio and sign/verify/hash/serialize throughput
  - `buffer_bench.py` — buffer memory footprint and add/evict/lookup throughput
  - `encryption_bench.py` — AES-256-GCM bulk and per-chunk throughput
  - `swarm_bench.py` — tree/mesh construction scaling, fanout, churn, node-removal reattachment
  - `retransmit_bench.py` — retransmission request/handle/timeout/recovery throughput
  - `incentives_bench.py` — tit-for-tat accounting and classification throughput
  - `proof_bench.py` — proof-of-relay receipt sign/verify/redeem throughput
  - `pipeline_bench.py` — end-to-end in-memory delivery model (depth, fan-out cost, latency)
  - CLI: `python -m qlive.benchmarks [suite ...] [--json] [--list]`
- `tests/python/test_benchmarks.py` — smoke tests covering the benchmark runner and all suites
- `qlive/simulation.py` — discrete-event swarm simulation (tree push + mesh pull, edge loss, retransmission, churn, parent-drop, free-riders)
- `qlive/benchmarks/sim_bench.py` — simulation scenario sweeps (fanout, mesh, retransmit, buffer, churn, free-riders)
- `tests/python/test_simulation.py` — 8 tests covering the simulation engine
- `src/js/` — React + Vite + TypeScript web application (first iteration, offline/mock)
  - `src/data/api.ts` — swappable data service abstraction (mock backend, no network required)
  - `src/data/liveStats.ts` — live stats client (WebSocket + offline simulator)
  - `src/pages/` — Discovery (search/sort/filter), Watch, Dashboard, and Profile views
  - `src/components/` — Layout, StreamCard (category thumbnails), Player (hls.js lazy-loaded), Stat, StatusBadge
  - `src/index.css` — dark-theme design system, responsive + accessibility
  - Vitest + Testing Library setup (8 unit tests) and Playwright e2e tests (`e2e/`)

### Fixed
- `qlive/swarm.py` — `DeliveryTree.find_parent` no longer selects unattached peers (mesh viewers) as tree parents, which previously flattened the delivery tree to depth 1 and defeated the depth-based latency model
- `tests/python/test_swarm.py` — regression test `test_attach_skips_unattached_peers`

---

*Changelog entries will be added as development progresses.*