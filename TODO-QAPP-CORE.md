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

### Concrete `qortalRequest` actions used
| Concern | qapp-core hook / util | qortalRequest action(s) | Notes |
| --- | --- | --- | --- |
| Auth / identity | `useAuth`, `useAuthStore` | `GET_USER_ACCOUNT`, `GET_PRIMARY_NAME` | Gives `address`, `publicKey`, `name`, `avatarUrl` |
| Publish stream metadata | `usePublish` (store `setPublish`) | `PUBLISH_QDN_RESOURCE`, `PUBLISH_MULTIPLE_QDN_RESOURCES` | `ResourceToPublish`: `service, identifier, name, base64/data64/file, encryption?: {encryptionType:'streamed-v1', iv, key}` |
| Fetch / play resource | `useResources.getPublishJson`, `GET_QDN_RESOURCE_URL` | `FETCH_QDN_RESOURCE`, `GET_QDN_RESOURCE_URL` | URL `/arbitrary/${service}/${name}/${identifier}` (`?encoding=base64` option) |
| List live streams | `useResources`, `useListReturn` | `LIST_QDN_RESOURCES`, `SEARCH_QDN_RESOURCES` | Builds `/arbitrary/resources/search?...&service=JSON&name=...&includemetadata=true` |
| Encryption (key envelopes) | `createIvAndKeyBase64` | — | AES-256 iv(16)+key(32) base64 ← matches per-stream envelope model |
| Name resolution | `createAvatarLink`, `createQortalLink` | — | Avatar = `/arbitrary/THUMBNAIL/${name}/qortal_avatar?async=true` |

### Authentication & Identity
- [ ] Replace mock broadcaster login with `useAuth` (Qortal Name / address)
- [ ] Derive QLive stream `publisher` from authenticated `useAuthStore.name`
- [ ] Bind broadcaster `address`/`publicKey` to chunk-signing key association (cross-check with `qlive/chunk.py` signing)
- [ ] Surface streamer avatar + "verified" badge from `useAuthStore`
- [ ] Handle `isLoadingUser` / `errorLoadingUser` states in dashboard & profile

### QDN / Stream signaling — schema mapping
QLive's `QDN Signaling Schema` (`docs/signaling-schema.md`) maps onto qapp-core like this:

- **Service / resource type:** publish `qlive-stream` JSON docs under QDN `Service.JSON` (or `METADATA`), identified by a reserved identifier (e.g. `QLIVE_STREAMS` per-name) and discovered via `SEARCH_QDN_RESOURCES` (`QortalSearchParams: service, name, keywords, query, followedOnly`).
- **Metadata envelope:** each QDN `QortalMetadata` carries `metadata.title/description/tags/category`, aligning to QLive's `title, description, category, thumbnail`. The stream's `status` lifecycle (`announced → live → ended → archived`) is mutated via `PUBLISH_QDN_RESOURCE` re-publish on state change (cadence per `QDN-SIGNALING-FREQUENCY.md`).
- **Swarm / keys:** live peer lists + encryption key envelopes are published as separate `Service.JSON` resources (or a `METADATA` companion object) and refreshed on the documented delta-triggered / 30–60s cadence.
- **Resource shape:** `useResources` resolves each stream to a `Resource = { qortalMetadata: QortalMetadata; data: any }` — `data` is the parsed `qlive-stream` document; `qortalMetadata.metadata.title` feeds discovery sort/filter.
- [ ] Implement stream-metadata QDN publish adapter (`usePublish` → `PUBLISH_QDN_RESOURCE`) replacing mock registry
- [ ] Enumerate active/upcoming/archived streams via `useResources`/`useListReturn` + `ResourceListDisplay` (replaces `src/data/api.ts` list)
- [ ] Fetch stream detail + peer list via `getPublishJson` (replaces mock `getStream`)
- [ ] Map QLive `category`/`tags`/`title` ↔ QDN metadata fields for Qortal search to succeed

### Media
- [ ] Evaluate `VideoPlayerParent` (props: `qortalVideoResource: QortalGetMetadata`, `encryption?: EncryptionConfig`, `timelineActions?: TimelineAction[]`, `autoPlay`, `poster`) for the archived/VOD watch path
- [ ] Note: QLive *live* playback uses the ephemeral mesh + WebSocket transport, not QDN direct-fetch — so `VideoPlayerParent` fits the **archived → Q-Tube** flow (Phase 3) via `GET_QDN_RESOURCE_URL`, while the live watch path keeps `hls.js`/mesh socket
- [ ] Reuse `ImagePicker` for stream thumbnails / broadcaster avatar uploads
- [ ] Reuse `sanitizedContent`/`processText` for stream descriptions

### Global state & i18n
- [ ] Migrate from the bespoke React-hooks `Api` to qapp-core zustand stores (`app`, `auth`, `cache`, `indexes`, `lists`, `publishes`)
- [ ] Mount `GlobalProvider` + `useGlobal` at the app root; reconcile with existing layout
- [ ] Adopt qapp-core's `Index` / `IndexCategory` types for the discovery "by category" view
- [ ] Adopt qapp-core i18n (loaded via `useLibTranslation`) for 11-locale support
- [ ] Use qapp-core event bus / toast (`showLoading`, `showSuccess`, `showError`, `dismissToast`) for consistent UX

---

## Migration of `src/data/api.ts` (Mock → Real)

> **Key constraint:** `qapp-core` resolves QDN via relative URLs (`/arbitrary/...`,
> `/arbitrary/resources/search?...`) and the global `qortalRequest()` function that
> the **Qortal UI host** injects at runtime. In QLive's standalone Vite dev server
> these don't resolve, so the mock `api.ts` seam must remain the default for offline
> dev/CI, with qapp-core only engaged when `qortalRequest` / a Qortal UI host is
> present (feature-flag / provider prop).

- [x] Keep `api.ts` as the seam; back it with qapp-core calls behind a toggle → `selectApi()` switch + `qapp.ts` adapter
- [x] Provide mock fallback for offline development / CI (no Qortal node) → `selectApi()` falls back to `api` (mock) when `window.qortalRequest` is absent
- [x] Manageability: keep API-boundary mocks for tests (per standards) → mock `Api` untouched; new adapter unit-testable via injected `QortalBackend`
- [ ] Document how to run offline vs. pointing at a local Qortal node
- [x] Tests: unit-test the adapter layer, not qapp-core internals → `src/data/qapp.test.ts` (8 tests, offline)

---

## Testing & QA

- [ ] Verify Web UI still builds after qapp-core adoption (`npm run build`)
- [ ] Type-check against qapp-core's types (`tsc --noEmit`) — *note: `src/js` currently has a pre-existing `hls.js` resolution error in `Player.tsx` unrelated to this work*
- [x] Keep Vitest suite green; add minimal tests for the integration seam — `qapp.test.ts` (8) + existing `api.test.ts` (6) all pass
- [ ] Manual smoke test with a running Qortal UI node (`qortalRequest` wired)

---

## Milestones

- [x] **Q1 — Vendor:** submodule added, documented, buildable
- [~] **Q1.5 — Seam (offline):** injectable QDN adapter `qapp.ts` + `selectApi()` toggle + seam tests (no host required)
- [ ] **Q2 — Foundation:** React 19 + MUI upgrade, GlobalStateProvider in place
- [ ] **Q3 — Auth & signaling:** Qortal auth + stream metadata over QDN
- [ ] **Q4 — Playback:** viewer video via qapp-core components
- [ ] **Q5 — De-mock:** real QDN storage path replaces mock default

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-26 | Add `qapp-core` as a vendored git submodule | Reuse Qortal's tested React foundation (auth, QDN CRUD, player, state) instead of building our own Qortal networking layer |
| 2026-08-26 | Model the QDN bridge as an injectable `QortalBackend`, not a direct qapp-core import | qapp-core has no `dist/` until built and needs a Qortal-UI host runtime; an injected backend keeps the adapter offline-testable and defers the React 19/MUI upgrade. `selectApi()` toggles mock↔QDN by host presence |

---

*This document is a living artifact. Update it as the integration evolves.*