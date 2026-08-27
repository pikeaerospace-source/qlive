# Architecture & Project Administration

## Project Overview

QLive is a **decentralized live streaming protocol** built on top of Qortal's infrastructure. See [README.md](../README.md) for the full project overview and architecture diagram.

---

## Project Structure

```
qlive/
├── .clinerules/         # AI coding agent rules (this directory)
│   ├── 01-coding-style.md
│   ├── 02-testing-standards.md
│   └── 03-architecture.md
├── .clineignore         # Files/directories excluded from AI context
├── docs/                # Protocol specs, design docs, research notes
├── qapp-core/           # Qortal UI library (git submodule — auth, QDN CRUD, player, state)
├── src/
│   ├── python/          # Python reference implementation
│   │   └── qlive/       #   Core modules (chunk, buffer, swarm, etc.)
│   ├── js/              # React + Vite + TypeScript web UI
│   └── java/            # Java (Qortal Core integration — forthcoming)
├── tests/
│   └── python/          # Python test suite
├── README.md            # Project overview & architecture
├── TODO.md              # Living roadmap & task tracking
├── TODO-QTUBE.md        # Q-Tube integration tasks
├── TODO-QORTAL-CORE.md  # Qortal Core integration tasks
├── TODO-QAPP-CORE.md    # qapp-core submodule integration tasks
├── TODO-WEB-UI.md       # Web UI tasks
├── TODO-RESEARCH.md     # Research & open design questions
├── CHANGELOG.md         # Release history (Keep a Changelog)
├── SECURITY.md          # Security policy & vulnerability reporting
├── CONTRIBUTING.md      # Contribution guidelines
├── AUTHORS.md           # Contributors list
├── LICENSE.md           # MIT License
├── .gitignore           # Git ignore rules
└── .editorconfig        # Cross-editor style settings
```

---

## Core Architecture (3-Layer Model)

1. **QDN / Chain Layer (Signaling)** — Stream metadata, peer lists, encryption keys on QDN.
2. **Ephemeral P2P Mesh (RAM Transport)** — CMAF/fMP4 chunks relayed via in-memory sliding-window buffer.
3. **QDN Archival (VOD Engine)** — Completed streams stitched and committed to QDN as Q-Tube content.

---

## Key Documents For AI Context

### Always Read These First When Starting A Session
- `README.md` — Project overview, architecture, getting started.
- `SECURITY.md` — Security policy, vulnerability reporting, threat model.
- `CHANGELOG.md` — What changed most recently, release history.
- `TODO.md` — Current tasks, open questions, milestones, decision log.

### Sub-TODO Documents (read when relevant)
- `TODO-QTUBE.md` — Q-Tube integration work.
- `TODO-QORTAL-CORE.md` — Qortal Core integration work.
- `TODO-WEB-UI.md` — React Web UI work.
- `TODO-RESEARCH.md` — Open research questions.

### Design Documents (in `docs/`)
- `docs/protocol.md` — Formal protocol specification v0.1.0.
- `docs/architecture.md` — Component architecture overview.
- `docs/chunk-format.md` — Ephemeral chunk binary format.
- `docs/swarm-protocol.md` — Dual-layer tree + mesh swarm.
- `docs/buffer-design.md` — RAM sliding-window buffer.
- `docs/signaling-schema.md` — QDN signaling metadata schema.
- `docs/vod-pipeline.md` — Live → VOD archival pipeline.
- `docs/incentives.md` — Tit-for-tat, proof-of-relay design.
- `docs/THREAT-MODEL.md` — STRIDE threat model & attack vectors.
- `docs/SECURITY-MODEL.md` — Sybil resistance, DoS resilience.
- `docs/ECONOMIC-MODELING.md` — Relay/streamer/viewer economics.
- `docs/SWARM-SIMULATION.md` — Discrete-event simulation findings.
- Research docs: `RETICULUM-INTEGRATION.md`, `NAT-TRAVERSAL.md`, `CHUNK-SIZE-TUNING.md`, `BUFFER-SIZING.md`, `QDN-SIGNALING-FREQUENCY.md`, `ENCRYPTION-MODEL.md`, `QORTAL-CORE-API.md`, `BANDWIDTH-MEASUREMENT.md`, `MONETIZATION.md`.

---

## Python Source Code Conventions
- Package: `src/python/qlive/`.
- Build: `pyproject.toml` at `src/python/`.
- Run tests: `cd src/python && pytest` (coverage report included).
- Benchmarks: `python -m qlive.benchmarks`.

## JavaScript/TypeScript Conventions
- Project: `src/js/`.
- Scripts: `dev`, `build`, `test`, `test:e2e` via `package.json`.
- Mock data: `src/js/src/data/mock.ts` — swap via `src/js/src/data/api.ts`.

---

## Administration Guidance For AI

When asked to make changes or add features:

1. **Read `TODO.md` first** to check if the task is already tracked.
2. **Check `CHANGELOG.md`** to understand recent work and what's already implemented.
3. **Check `SECURITY.md`** before touching encryption, signing, or network code.
4. **Check `CONTRIBUTING.md`** for PR process and commit message format.
5. **Follow file header templates** from `01-coding-style.md`.
6. **Follow test patterns** from `02-testing-standards.md`.
7. **Always verify** new code passes existing tests before declaring done.
8. **Keep AI responses concise** — prefer showing only changed/diff content in responses to reduce token spend.
