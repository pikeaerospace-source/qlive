# QLive — Web UI & Frontend TODO

Tracking tasks for building the QLive web interface, including the broadcaster dashboard, viewer player, and stream discovery.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Overview

The QLive web UI provides:
1. **Broadcaster dashboard** — manage streams, monitor health, view stats
2. **Viewer player** — watch live streams with adaptive bitrate
3. **Stream discovery** — browse active and upcoming streams
4. **Streamer profiles** — show streamer info and past streams

---

## Broadcaster Dashboard

- [x] Web UI for stream management (start/stop, preview, stats)
- [x] Publish stream metadata on start/stop (QDN signaling via `selectPublisher()`; offline in-memory registry)
- [x] Stream configuration form (title, description, category, bitrate)
- [ ] Live preview of the stream
- [x] Start/stop broadcast controls
- [x] Stream health dashboard (viewer count, bandwidth, buffer status)
- [x] Archive status indicator — dashboard shows "Archiving…" once the ended doc is published, then "Archived" once the stream-doc read-back reports the archive is complete (polls `getStream` while archiving)
- [~] Error and warning notifications (publish/signaling failures surfaced; stream/encoder warnings pending)

### Dashboard Features
- [x] Real-time viewer count — from the live stats feed (`subscribeStats`)
- [x] Bandwidth usage graph — `Sparkline` of a rolling bandwidth window
- [x] Buffer health indicator — colour-toned stat (`filling`/`healthy`/`stalling`/`overflow`)
- [x] Chunk production rate — session-average chunks/min
- [x] Retransmission statistics — cumulative count from the stats feed
- [ ] QORT earnings display (if monetized)

---

## Viewer Player

- [~] Web player (HLS/CMAF playback, low-latency mode) — hls.js wired, mock placeholder
- [x] Play/pause controls — custom control bar (native `controls` removed)
- [x] Volume and fullscreen controls — mute toggle + volume slider + fullscreen button (auto-disabled where unsupported)
- [x] Adaptive bitrate indicator — quality selector reflects hls.js ABR level switches (`LEVEL_SWITCHED`)
- [x] Buffer health indicator — control-bar chip (`buffering`/`low`/`healthy`) derived from the buffered-ahead window + a `bufferHealth()` helper
- [x] Stream quality selector — `select` listing Auto + each manifest rendition, wired to `hls.currentLevel` (falls back to a static "Source" label with no advertised renditions)
- [x] Chat panel (optional) — ephemeral stream chat (`data/chat.ts` seam + `ChatPanel`), shown on the watch page for live streams

### Player Features
- [x] Low-latency mode toggle — on by default for live, hidden for replays; toggling rebuilds the hls.js pipeline (constructor option)
- [x] Picture-in-picture support — control-bar button + `I` shortcut (feature-detected; disabled where unsupported)
- [x] Keyboard shortcuts — Space/K play-pause, M mute, F fullscreen, I picture-in-picture, ↑/↓ volume (scoped to the player, ignored while typing in inputs)
- [ ] Mobile responsive layout
- [x] Error recovery (reconnect on stream drop) → `Player` playback states: auto-recovery (2× backoff on network errors, 1× media-error recovery) then a "Playback interrupted" overlay with Retry
- [x] Playback status overlay (connecting / reconnecting / interrupted / unsupported)

---

## Stream Discovery

- [x] Stream discovery UI (browse active streams)
- [x] Browse live streams by category
- [x] Browse upcoming (announced) streams
- [x] Search streams by title or streamer
- [x] Stream cards with thumbnail, title, viewer count
- [x] Sort and filter options

### Discovery Features
- [x] Featured streams section — curated `Stream.featured` row (disjoint from Trending)
- [x] Trending streams (by viewer count) — top live streams row, cap 3, excludes featured
- [x] Recently ended streams (with replay links)
- [x] Followed streamers section — "Following" row driven by the offline follow store (`src/js/src/data/follows.ts`)

---

## Streamer Profiles

- [x] Streamer profile page
- [x] Show active streams
- [x] Show past streams (VOD)
- [x] Show streamer bio and stats
- [x] Follow/unfollow button — offline `localStorage`-backed follow store (`follows.ts`), `aria-pressed` toggle
- [ ] Notification preferences

---

## Design & UX

- [x] Design system (colors, typography, spacing)
- [x] Dark mode support
- [~] Responsive layout (desktop, tablet, mobile)
- [~] Accessibility (WCAG 2.1)
- [x] Loading states and skeletons — `Skeleton` component (`grid`/`text`/`detail` variants) on Discovery, Watch, and Profile while fetching
- [x] Empty states — Discovery "no match", Profile "no streams yet", Dashboard "no broadcast yet" before the first stream
- [x] Error states — page-level fetch failures surface a `notice--error` with **Retry** on Discovery, Watch, and Profile (player playback interruptions already covered by the Player overlay)

---

## Frontend Architecture

> **Foundation:** Starting 2026-08-26 the Web UI vendors Qortal's **`qapp-core`**
> library (submodule at `qapp-core/`) for auth, QDN CRUD, player components, and
> global state. Adopting it requires the React 19 + MUI v7 + Router 7 migration
> tracked in [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md). The tasks below have been re-scoped
> around that foundation where relevant.

- [x] Choose frontend framework (React/Vue/Svelte) → **React 18** (→ **19** via qapp-core)
- [x] Set up build tooling (Vite/Webpack) → **Vite 5**
- [~] Set up state management → migrate to `qapp-core` zustand stores + `GlobalProvider` → [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md)
- [x] Set up routing → React Router 6 (upgrade **7** via qapp-core)
- [x] Set up API client for QLive backend → QDN adapters in `qapp.ts`/`publisher.ts` (read + publish) exposed through the `selectApi()`/`selectPublisher()` seams and consumed by the pages/dashboard (qapp-core hooks adoption deferred with `GlobalProvider`) → [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md)
- [x] Set up WebSocket client for real-time updates
- [x] Set up testing framework → Vitest + Testing Library

### Components
- [x] Player component
- [x] Stream card component
- [x] Streamer profile component
- [x] Chat component — `ChatPanel` (`src/js/src/components/ChatPanel.tsx`)
- [x] Dashboard widgets

---

## Testing & QA

- [x] Unit tests for components
- [x] Integration tests for player (data service)
- [x] End-to-end tests for broadcast flow
- [~] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Mobile testing (iOS, Android)
- [ ] Performance testing (page load, playback smoothness)

---

## Milestones

- [~] **W1 — Player:** Basic live stream playback works in browser (hls.js wired; real stream pending)
- [x] **W2 — Discovery:** Users can browse and find streams
- [x] **W3 — Dashboard:** Streamers can manage broadcasts
- [x] **W4 — Profiles:** Streamer profiles with live and VOD content
- [~] **W5 — Polish:** Design system, mobile, accessibility (design done; mobile/a11y partial)

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-26 | Adopt `qapp-core` (submodule) as the Web UI foundation | Reuse Qortal's tested auth / QDN CRUD / player / state instead of hand-rolling the Qortal layer; requires React 19 + MUI 7. Tracks in [TODO-QAPP-CORE.md](TODO-QAPP-CORE.md) |
| 2026-09-22 | Split discovery into a live/upcoming grid and a separate "Recently ended" replay section | Replays are not live; a dedicated section gives them archive metrics + replay links, and keeps the main grid focused on what is watchable now. Replay state is derived once from `Stream.archive` so QDN and mock data behave identically |

---

*This document is a living artifact. Update it as the UI evolves.*