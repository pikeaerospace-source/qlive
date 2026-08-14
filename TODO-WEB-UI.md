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
- [x] Stream configuration form (title, description, category, bitrate)
- [ ] Live preview of the stream
- [x] Start/stop broadcast controls
- [x] Stream health dashboard (viewer count, bandwidth, buffer status)
- [ ] Archive status indicator
- [ ] Error and warning notifications

### Dashboard Features
- [ ] Real-time viewer count
- [ ] Bandwidth usage graph
- [ ] Buffer health indicator
- [ ] Chunk production rate
- [ ] Retransmission statistics
- [ ] QORT earnings display (if monetized)

---

## Viewer Player

- [~] Web player (HLS/CMAF playback, low-latency mode) — hls.js wired, mock placeholder
- [ ] Play/pause controls
- [ ] Volume and fullscreen controls
- [ ] Adaptive bitrate indicator
- [ ] Buffer health indicator
- [ ] Stream quality selector
- [ ] Chat panel (optional)

### Player Features
- [ ] Low-latency mode toggle
- [ ] Picture-in-picture support
- [ ] Keyboard shortcuts
- [ ] Mobile responsive layout
- [ ] Error recovery (reconnect on stream drop)

---

## Stream Discovery

- [x] Stream discovery UI (browse active streams)
- [x] Browse live streams by category
- [x] Browse upcoming (announced) streams
- [x] Search streams by title or streamer
- [x] Stream cards with thumbnail, title, viewer count
- [x] Sort and filter options

### Discovery Features
- [ ] Featured streams section
- [ ] Trending streams (by viewer count)
- [ ] Recently ended streams (with replay links)
- [ ] Followed streamers section

---

## Streamer Profiles

- [x] Streamer profile page
- [x] Show active streams
- [x] Show past streams (VOD)
- [x] Show streamer bio and stats
- [ ] Follow/unfollow button
- [ ] Notification preferences

---

## Design & UX

- [x] Design system (colors, typography, spacing)
- [x] Dark mode support
- [~] Responsive layout (desktop, tablet, mobile)
- [~] Accessibility (WCAG 2.1)
- [ ] Loading states and skeletons
- [ ] Empty states
- [ ] Error states

---

## Frontend Architecture

- [x] Choose frontend framework (React/Vue/Svelte) → **React 18**
- [x] Set up build tooling (Vite/Webpack) → **Vite 5**
- [x] Set up state management → React hooks + `Api` service abstraction
- [x] Set up routing → React Router 6
- [x] Set up API client for QLive backend → `src/data/api.ts` (mock, swappable)
- [x] Set up WebSocket client for real-time updates
- [x] Set up testing framework → Vitest + Testing Library

### Components
- [x] Player component
- [x] Stream card component
- [x] Streamer profile component
- [ ] Chat component
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
| — | — | — |

---

*This document is a living artifact. Update it as the UI evolves.*