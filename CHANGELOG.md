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

---

*Changelog entries will be added as development progresses.*