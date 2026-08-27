# QLive — qapp-core (Q-App) Integration TODO

Tracking tasks for integrating **`qapp-core`** — Qortal's core React library — into
the QLive Web UI. `qapp-core` is vendored as a git submodule at `qapp-core/`
(remote: `git@github.com:pikeaerospace-source/qapp-core.git`).

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Overview

`qapp-core` is an npm library that abstracts common Qortal multi-layer work so
QLive does not need to re-implement the Qortal networking layer. It provides:

1. **Authentication & identity** — `useAuth`, user account / primary-name /
   avatar management, account switching.
2. **QDN CRUD** — `usePublish`, `useResources`, `useAllResourceStatus`,
   `useResourceStatus` for publishing, fetching, and listing QDN resources.
3. **Reusable components** — `VideoPlayer`/`AudioPlayer`, `ResourceListDisplay`
   (grid/list pagination), `ImagePicker`, `VirtualizedList`, `GlobalProvider
   modal/toast/loading helpers.
4. **Global state (zustand)** — `app`, `auth`, `cache`, `indexes`, `lists`,
   `multiplePublish`, `pip`, `publishes`, `video` stores.
5. **Qortal API surface** — a typed `qortalRequest(options)` bridge to the
   Qortal UI node (QDN publish/list/fetch, names, coins, groups, encryption).
6. **Utilities & i18n** — encryption (AES-256/symmetric key), base64, event bus,
   sanitized content, number/time formatting, 11 locale packs.

By adopting `qapp-core`, QLive's Web UI can replace its offline mock
`src/data/api.ts` layer with real Qortal/QDN interactions on a shared, tested
foundation.

---

## Vendoring / Submodule

- [x] Add `qapp-core` as a git submodule at `qapp-core/` (pinned commit)
- [x] Document clone/init instructions in `README.md`
- [ ] Pin a stable release tag/commit for reproducible builds
- [ ] Confirm upstream `qapp-core` is buildable (`npm install && npm run build`)
- [ ] Decide vendoring strategy (submodule vs. npm dependency) before public release

---

## Web-UI Integration Prerequisites

`qapp-core` has these peer dependencies; the QLive Web UI must adopt them:

- [ ] Migrate **React 18 → 19** (`src/js/package.json`)
- [ ] Adopt **MUI v7** (`@mui/material`, `@mui/icons-material`, `@emotion/*`)
- [ ] Upgrade **React Router 6 → 7** to match qapp-core's peer range
- [ ] Wire up `GlobalProvider` + `useGlobal` at the app root
- [ ] Import `qapp-core/index.css` and adopt its theme tokens
- [ ] Decide how qapp-core's zustand stores coexist with existing React-hooks state

---

## QLive Feature Mapping

### Authentication & Identity
- [ ] Replace mock broadcaster login with `useAuth` (Qortal Name / address)
- [ ] Show authenticated streamer (avatar, name) in dashboard & profile
- [ ] Gate broadcaster controls behind authenticated Qortal Name
- [ ] Use resolved identity for chunk signing key association

### QDN / Stream signaling
- [ ] Publish stream metadata via `usePublish` (replaces mock registry)
- [ ] Enumerate active/upcoming streams via `useResources` + `ResourceListDisplay`
- [ ] Fetch stream metadata + peer lists from QDN using `useListData`
- [ ] Map QLive signaling schema to `QortalMetadata` resource types

### Media
- [ ] Evaluate `VideoPlayer`/`AudioPlayer` for the viewer experience
- [ ] Integrate live playback with qapp-core's video/encryption utilities
- [ ] Reuse `ImagePicker` for stream thumbnails / avatars

### Global state & i18n
- [ ] Adopt qapp-core stores for app-wide state instead of bespoke hooks
- [ ] Enable qapp-core's i18n (11 locales) for the UI
- [ ] Use qapp-core event bus / toast / loading helpers for consistent UX

---

## Migration of `src/data/api.ts` (Mock → Real)

- [ ] Keep `api.ts` as the seam; back it with qapp-core calls behind a toggle
- [ ] Provide mock fallback for offline development / CI (no Qortal node)
- [ ] Manageability: keep API-boundary mocks for tests (per standards)
- [ ] Document how to run offline vs. pointing at a local Qortal node
- [ ] Tests: unit-test the adapter layer, not qapp-core internals

---

## Testing & QA

- [ ] Verify Web UI still builds after qapp-core adoption (`npm run build`)
- [ ] Type-check against qapp-core's types (`tsc --noEmit`)
- [ ] Keep Vitest suite green; add minimal tests for the integration seam
- [ ] Manual smoke test with a running Qortal UI node (`qortalRequest` wired)

---

## Milestones

- [~] **Q1 — Vendor:** submodule added, documented, buildable
- [ ] **Q2 — Foundation:** React 19 + MUI upgrade, GlobalStateProvider in place
- [ ] **Q3 — Auth & signaling:** Qortal auth + stream metadata over QDN
- [ ] **Q4 — Playback:** viewer video via qapp-core components
- [ ] **Q5 — De-mock:** real QDN storage path replaces mock default

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-26 | Add `qapp-core` as a vendored git submodule | Reuse Qortal's tested React foundation (auth, QDN CRUD, player, state) instead of building our own Qortal networking layer |

---

*This document is a living artifact. Update it as the integration evolves.*