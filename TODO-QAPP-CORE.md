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
- [~] Pin a stable release tag/commit for reproducible builds
- [x] Confirm upstream `qapp-core` is buildable (`npm install && npm run build`) — builds `dist/{index.js,index.mjs,index.d.ts}` (fixed a corrupted `video.js` types install in this env)
- [ ] Decide vendoring strategy (submodule vs. npm dependency) before public release

---

## Web-UI Integration Prerequisites

`qapp-core` has these peer dependencies; the QLive Web UI must adopt them:

- [x] Migrate **React 18 → 19** (`src/js/package.json`) — `react`/`react-dom` `^19.0.0`
- [x] Adopt **MUI v7** (`@mui/material` `^7.0.1`, `@mui/icons-material` `^7.0.1`, `@emotion/react` + `@emotion/styled`)
- [x] Upgrade **React Router 6 → 7** (`react-router-dom` `^7.6.2`)
- [ ] Upgrade dev toolchain to match (`@vitejs/plugin-react` `^5`, `vitest` `^2`, `@types/react` `^19`, `eslint` `^9`, `@typescript-eslint` `^8`) — done; validated `tsc`/`vitest`/`vite build` green
- [ ] Wire up `GlobalProvider` + `useGlobal` at the app root — **deferred** (see Milestones Q2.5; provider mounts host-dependent auth/indexes hooks, staged after auth is implemented)
- [ ] Import `qapp-core/index.css` and adopt its theme tokens — deferred with `GlobalProvider`
- [~] Decide how qapp-core's zustand stores coexist with existing React-hooks state — keep `qapp.ts` adapter as the data seam; migrate component state incrementally

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
- [ ] Implement stream-metadata QDN publish adapter (`usePublish` → `PUBLISH_QDN_RESOURCE`) replacing mock registry — next, to add to `qapp.ts`
- [~] Enumerate active/upcoming/archived streams via search → `listStreams` in `qapp.ts` (QDN `SEARCH_QDN_RESOURCES` + `FETCH_QDN_RESOURCE`, prefix/status filtered)
- [~] Fetch stream detail → `getStream` in `qapp.ts` (QDN `FETCH_QDN_RESOURCE` by `qliveStreamIdentifier`, search fallback)
- [x] Map QLive `category`/`tags`/`title` ↔ QDN metadata fields — `toStream`/`searchStreams` map the `qlive-stream` doc ↔ `QortalMetadata`

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

- [x] Verify Web UI still builds after qapp-core adoption (`npm run build` = `tsc --noEmit` + `vite build`, both green)
- [x] Type-check against qapp-core's types (`tsc --noEmit`, exit 0) — qapp-core resolved via `type` bridge; the pre-existing `hls.js` resolution error was repaired (corrupted `video.js` types install) during the env rebuild
- [x] Keep Vitest suite green; add minimal tests for the integration seam — `qapp.test.ts` (8) + existing `api.test.ts` (6) all pass (16/16)
- [ ] Manual smoke test with a running Qortal UI node (`qortalRequest` wired) — blocked on Q3 auth; `GlobalProvider` not yet mounted

---

## Milestones

- [x] **Q1 — Vendor:** submodule added, documented, buildable
- [x] **Q1.5 — Seam (offline):** injectable QDN adapter `qapp.ts` + `selectApi()` toggle + seam tests (no host required) — 16/16 tests, `tsc` + `vite build` green
- [x] **Q2 — Foundation:** React 19 + MUI v7 + Router 7 + qapp-core dep, validated green
- [~] **Q2.5 — Provider:** mount `GlobalProvider` + qapp-core CSS — *deferred* (host-dependent auth/indexes; gated on Q3 auth)
- [ ] **Q3 — Auth & signaling:** Qortal auth + stream metadata publish over QDN
- [ ] **Q4 — Playback:** viewer video via qapp-core components
- [ ] **Q5 — De-mock:** real QDN storage path replaces mock default

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-26 | Add `qapp-core` as a vendored git submodule | Reuse Qortal's tested React foundation (auth, QDN CRUD, player, state) instead of building our own Qortal networking layer |
| 2026-08-26 | Model the QDN bridge as an injectable `QortalBackend`, not a direct qapp-core import | qapp-core has no `dist/` until built and needs a Qortal-UI host runtime; an injected backend keeps the adapter offline-testable and defers the React 19/MUI upgrade. `selectApi()` toggles mock↔QDN by host presence |
| 2026-08-26 | Upgrade QLive Web UI toolchain to match qapp-core peers (React 19, react-dom 19, react-router-dom 7, MUI v7 + `@emotion/*`, `@vitejs/plugin-react` ^5, `vitest` ^2, `@types/react` ^19, `eslint` ^9, `@typescript-eslint` ^8) | Required so qapp-core's peer deps resolve; `qapp-core` declared as `file:../../qapp-core` |
| 2026-08-26 | Repair corrupted `video.js` types install & fix symlink path | The interrupted env installs left `video.js` without `*.d.ts` (broke qapp-core's `tsc`); reinstalled to restore types so qapp-core builds. `file:../../qapp-core` (not `../qapp-core`) is the correct relative spec from `src/js/`; verified `tsc --noEmit`=0, `vitest`=16/16, `vite build`=exit 0 |

---

*This document is a living artifact. Update it as the integration evolves.*