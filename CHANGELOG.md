# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

- `qlive/chunk.py` — chunks now sign **only the header** (91 bytes, which embeds
  the SHA-256 `payload_hash`) instead of `header + payload`, making Ed25519
  sign/verify cost constant regardless of bitrate. Implements the documented
  decision (docs/ENCRYPTION-MODEL.md §2/§5, "Sign payload hash, not payload").
  Integrity is preserved: payload tampering changes the signed payload hash.
  Tests updated (`test_signing_data_covers_header_only`,
  `test_tampered_header_fails_verification`); docs (`chunk-format.md`,
  `THREAT-MODEL.md`, `ENCRYPTION-MODEL.md`, `CHUNK-SIZE-TUNING.md`) reflect it.
- Docs consistency: `protocol.md` §3.2/§3.3 now describe the header-only
  signature; `SECURITY-MODEL.md` §3 now reflects that receipts carry a
  `start_sequence`/`end_sequence` range (double-counting already prevented).

### Design

- `docs/MINTING-INTEGRATION.md` — explore proof-of-relay ↔ Qortal minting
  weight / node reputation (completes TODO.md Phase 4 + TODO-QORTAL-CORE
  Minting). Phased recommendation: off-chain relay reputation tracker now
  (offline-capable, from verified receipts), optional bonded relays, and the
  on-chain minting-weight feed deferred to Qortal Core availability.

### Added

- Web UI: **followed streamers + discovery rows** — a new offline
  `localStorage`-backed follow store (`src/js/src/data/follows.ts`, with
  `isFollowing`/`toggleFollow`/`listFollowing`/`subscribe`) drives a
  **Follow/Following** toggle on the streamer profile (persists across mounts)
  and a **"Following"** row on Discover. Discover also gains a curated
  **"Featured"** row (new optional `Stream.featured`, threaded through the QDN
  doc) and a **"Trending now"** row (top live streams by viewers, cap 3,
  disjoint from Featured); the live grid is now labelled "Live & upcoming", and
  the section markup is factored into a shared `StreamSection`. Tests:
  `follows.test.ts` (new, 6), `DiscoveryPage.test.tsx` (+4),
  `ProfilePage.test.tsx` (+2) — suite **105 passing** (was 93)
- Web UI: **player depth — picture-in-picture, low-latency toggle, buffer
  health** — the `Player` control bar gains a **PiP** button (feature-detected
  via `document.pictureInPictureEnabled`; disabled where unsupported) with an `I`
  keyboard shortcut, a **low-latency** toggle (on by default for live, hidden for
  replays; toggling rebuilds the hls.js pipeline since `lowLatencyMode` is a
  constructor option), and a **buffer-health chip**
  (`buffering`/`low`/`healthy`) driven by a new exported `bufferHealth()` helper
  over the buffered-ahead window. Tests: `Player.test.tsx` (22, was 15) — suite
  **93 passing** (was 86)
- Web UI: **archive completion read-back** on the broadcaster dashboard — while
  a stream is archiving, the dashboard polls `selectApi().getStream()` (every 5 s,
  `ARCHIVE_POLL_MS`) and, once the stream doc reports `status: archived`, replaces
  the "Archiving…" notice with an "Archived" notice and switches the **Status**
  stat to `Archived`. Closes the previous caveat that the dashboard could only
  show that archiving had *started*. Test: `DashboardPage.test.tsx` (+1) — suite
  **86 passing** (was 85)
- `tests/python/test_archival.py` — added integrity cases: tampering the
  **first** QDN chunk (caught by the chain link into the next chunk) and the
  empty-buffer `_flush()` guard (never reached via the public API, so exercised
  directly). `qlive/archival.py` now **99%** covered (was 98%); the one
  remaining branch (`verify_integrity`'s recomputed-hash comparison) is a
  defensive tautology — `QDNDataChunk.hash` is derived from `data`, so it always
  equals the recomputation once the chain link matches.
- Docs + tests: **Q-Tube manifest mapping** — `docs/qtube-integration.md`
  documents QLive's emitted `QTubeManifest` schema and a proposed
  field-by-field mapping to Q-Tube's expected format (required-vs-optional
  marked), plus the chunked-video / naming / envelope questions and open items
  for the Q-Tube team. `tests/python/test_qtube_compat.py` (14 tests) validates
  a representative manifest against those invariants — the discriminator,
  hex64 `streamId`, SHA-256 `chunkHashes`, epoch-ms ordering, JSON types, and
  the `isPartial` flag — with a fixture standing in for Q-Tube's reader until
  its authoritative schema is confirmed.

- Web UI: **player control bar + keyboard shortcuts** — `Player` now renders a
  custom control bar (play/pause, mute, volume slider, fullscreen, quality
  label, and a live-edge badge on live streams) instead of the native `controls`
  attribute, with keyboard shortcuts Space/K (play-pause), M (mute), F
  (fullscreen), and ↑/↓ (volume) scoped to the player so they never hijack
  typing in page inputs. `fullscreen` support is feature-detected and the
  button disables itself where unavailable. Tests: `Player.test.tsx` (15, was
  9)
- Web UI: **loading, empty, and error states** across pages — a new
  `Skeleton` component (`grid`/`text`/`detail` variants, `aria-hidden`) renders
  while Discovery/Watch/Profile fetch; failed fetches surface a
  `notice--error` with a **Retry** button that re-runs the request; empty states
  cover Discovery's no-match, Profile's no-streams, and the dashboard's
  pre-broadcast stats row. Tests: `ProfilePage.test.tsx` (new, 5),
  `DiscoveryPage.test.tsx` (+2), `WatchPage.test.tsx` (+2),
  `DashboardPage.test.tsx` (+1) — suite **85 passing** (was 69)
- Web UI: **archive status indicator** on the broadcaster dashboard — after
  **Stop broadcast** publishes the `ended` doc, the dashboard shows an
  `Archiving…` notice (`.notice--archiving`) and the **Status** stat reads
  `Archiving` instead of `Idle`, reflecting that the VOD engine has picked the
  stream up (docs/vod-pipeline.md). The dashboard has no read-back of archive
  *completion* yet, so it can only show that archiving started, not that it
  finished. Tests: `DashboardPage.test.tsx` (1 new —
  `shows an archiving indicator once the broadcast stops`) — suite
  **69 passing** (was 68)
- Web UI: **player error recovery** — `Player` now tracks a `PlaybackState`
  (`connecting` / `playing` / `recovering` / `interrupted` / `unsupported`) and
  survives stream drops: fatal hls.js **network** errors resume loading twice
  with a 1.5 s backoff, fatal **media** errors call `recoverMediaError()` once,
  and once recovery is exhausted a "Playback interrupted" overlay offers a
  **Retry** that rebuilds the pipeline from scratch (old instance destroyed). The
  native-HLS (Safari) path re-attaches the source, unsupported browsers get an
  explicit message, non-fatal errors are ignored, and counters reset once
  playback resumes. CSS: `.player-wrap` / `.player-overlay`; tests:
  `Player.test.tsx` (9, `hls.js` mocked incl. the dynamic import) — suite
  **68 passing** (was 59)
- Web UI: **activated the QDN seams** and wired the broadcaster dashboard to the
  publish path
    - pages now read through `selectApi()` (Watch/Discovery/Profile) instead of
      importing the mock `api` directly — previously `selectApi()` was unused, so a
      Qortal UI host would still have rendered mock data
    - `src/js/src/data/publisher.ts` — `selectPublisher()` write seam plus
      `MockStreamPublisher`, an in-memory registry used offline (`getDoc`,
      `streamIds`, `clear`); nothing leaves the browser without a host
    - `DashboardPage` publishes `live` on **Start broadcast** and re-publishes
      `ended` on **Stop broadcast** using the same stream id (QDN resource updated
      in place), surfacing a signaling panel (identifier/service/publisher/status)
      or an error notice; a new session gets a fresh id
    - `src/index.css` — `.notice--success` / `.notice--error`
    - tests: `publisher.test.ts` (5) + `DashboardPage.test.tsx` (4); page tests now
      mock the seam — suite **59 passing** (was 50)
- Web UI: **QDN publish (write) path** — `createStreamPublisher` /
  `qliveStreamPublisher` in `src/js/src/data/qapp.ts` (re-exported from `api.ts`)
  publish a stream's `qlive-stream` doc via `PUBLISH_QDN_RESOURCE` (`data64` =
  base64 doc, `title`/`category`/`tags` QDN metadata, identifier
  `QLIVE_STREAM_<streamId>`), plus `unpublishStream` (tombstone) and
  `streamToPublication` for lifecycle re-publish
  (`announced → live → ended → archived`). Requires an authenticated Qortal Name
  (`options.name` or host `qortalName`) and fails loudly without one.
  `QLiveStreamDoc` gains the `type: "qlive-stream"` marker and a typed `archive`
  ref (`QLiveArchiveRef`); `qapp.test.ts` 11 → 18 tests (suite **50 passing**)
- Web UI: **live → VOD replay** (completes TODO.md Phase 3 *Q-Tube Integration*)
    - `src/types.ts` — `ArchiveStatus` + `StreamArchive` (QDN resource ids, status,
      duration/size/fragment metrics) and `Stream.archive`
    - `src/data/archive.ts` — replay-state helpers: `replayState`
      (`none`/`archiving`/`ready`/`partial`), `hasReplay`, `replayLabel`,
      `replaySortKey`, `formatDuration`, `formatBytes`
    - `src/data/qapp.ts` — QDN adapter now maps the doc's `archive` block
      (`archiveFromDoc`; unknown status → `pending`) so QDN-backed streams report
      replay state too
    - `StreamCard` — "Watch replay ▸" / "Watch partial replay ▸" link, archive
      duration, and a "Replay archiving…" placeholder for finished-but-unpublished
      streams
    - `WatchPage` — replay notice with duration/size/fragment metrics, a
      **Watch replay** link to the QDN resource, a partial-archive warning, and an
      "Archiving…" notice; live-stat subscription now only runs while live and the
      stat row switches to archive metrics for replays
    - `DiscoveryPage` — new "Recently ended" section listing replays (sorted by
      publish time) plus a `Replays` stat; the main grid is now live + upcoming only
    - `Player` — `lowLatencyMode` only for live playback; replays play the same
      archived fragments at normal latency (**no re-encoding**)
    - `src/index.css` — `.notice`/`.section-title`/`.stream-card__replay` styles
- Web UI tests: `src/data/archive.test.ts` (12), `src/pages/WatchPage.test.tsx` (5),
  `src/pages/DiscoveryPage.test.tsx` (4), plus StreamCard replay cases and QDN
  archive-mapping cases — Web UI suite now **43 passing** (was 16)
- Docs: `docs/vod-pipeline.md` gains a **Viewer Replay UX** section documenting the
  replay state machine and the no-re-encoding playback path
- `qlive/reputation.py` — off-chain relay reputation tracker (time decay,
  diversity weighting, capped contribution, dispute window, receipt dedup; drives
  routing priority + bounty ordering), with `benchmarks/reputation_bench.py` and
  `tests/python/test_reputation.py` — the "off-chain relay reputation now" phase of
  `docs/MINTING-INTEGRATION.md`
- Add **`qapp-core`** as a vendored git submodule (`qapp-core/`)
    - Qortal core React library: auth (`useAuth`), QDN CRUD (`usePublish`, `useResources`), player & resource-list components, zustand global state, i18n, typed `qortalRequest` bridge
    - `TODO-QAPP-CORE.md` — integration plan (React 19 / MUI 7 migration, de-mocking `src/data/api.ts`, auth + QDN signaling)
    - `docs/architecture.md`, `README.md`, `TODO.md`, `TODO-WEB-UI.md`, `TODO-QORTAL-CORE.md` updated to track the submodule - Web UI: `src/data/qapp.ts` injectable QDN `Api` adapter (mirrors `qortalRequest` actions: `SEARCH_QDN_RESOURCES`, `FETCH_QDN_RESOURCE`, `GET_NAME_DATA`), `selectApi()` mock↔QDN toggle in `src/data/api.ts`, plus offline seam tests (`qapp.test.ts`, 8 cases; full suite 16 passing)
    - Web UI toolchain upgrade to match `qapp-core` peers: React 18→**19**, `react-router-dom` 6→**7**, added **MUI v7** + `@emotion/*`, `@vitejs/plugin-react` ^5, `vitest` ^2, `@types/react` ^19, `eslint` ^9, `@typescript-eslint` ^8; `qapp-core` added as `file:../../qapp-core` dependency. Validated: `tsc --noEmit` clean, `vitest` 16/16, `vite build` exit 0
    - `qapp-core` type bridge in `qapp.ts` (`import type { QortalMetadata } from "qapp-core"`) proving the vendored dependency resolves for typechecking; `GlobalProvider` mount deferred to Q3 (host-dependent auth)
- Docs: `WEB-UI-DATA-SOURCES.md` — how to run the Web UI against the offline mock (default) vs. pointing at a local Qortal node / QDN (Qortal-UI host injection, `qortalRequest` dev shim, `QortalBackend` injectable); resolves `selectApi()`'s host-presence check; linked from `README.md` + `docs/README.md`
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

- Security, simulation & economics research
    - `docs/SWARM-SIMULATION.md` — discrete-event swarm simulation findings (fanout, mesh, retransmit, buffer, churn, free-riders)
    - `docs/THREAT-MODEL.md` — STRIDE threat model and attack vectors (chunk injection, swarm manipulation, economic attacks)
    - `docs/SECURITY-MODEL.md` — sybil resistance, DoS resilience, receipt-forgery analysis, key distribution
    - `docs/ECONOMIC-MODELING.md` — relay/streamer/viewer economics, proof-of-relay design, free-rider cost
    - Component reference docs: `architecture.md`, `signaling-schema.md`, `chunk-format.md`, `swarm-protocol.md`, `buffer-design.md`, `vod-pipeline.md`, `incentives.md`
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
- `qlive/encryption.py` — per-stream AES-256-GCM encryption, key rotation, hybrid key envelopes
- `tests/python/test_encryption.py` — 6 tests covering encryption
- `qlive/proof.py` — bandwidth receipts now carry a `start_sequence`/`end_sequence` range to reject double-counting
- `qlive/signaling.py` / `broadcaster.py` / `viewer.py` — multi-bitrate renditions wired through metadata, config, and the adaptive controller
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

_Changelog entries will be added as development progresses._
