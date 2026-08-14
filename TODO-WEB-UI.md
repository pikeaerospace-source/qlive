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

- [ ] Web UI for stream management (start/stop, preview, stats)
- [ ] Stream configuration form (title, description, category, bitrate)
- [ ] Live preview of the stream
- [ ] Start/stop broadcast controls
- [ ] Stream health dashboard (viewer count, bandwidth, buffer status)
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

- [ ] Web player (HLS/CMAF playback, low-latency mode)
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

- [ ] Stream discovery UI (browse active streams)
- [ ] Browse live streams by category
- [ ] Browse upcoming (announced) streams
- [ ] Search streams by title or streamer
- [ ] Stream cards with thumbnail, title, viewer count
- [ ] Sort and filter options

### Discovery Features
- [ ] Featured streams section
- [ ] Trending streams (by viewer count)
- [ ] Recently ended streams (with replay links)
- [ ] Followed streamers section

---

## Streamer Profiles

- [ ] Streamer profile page
- [ ] Show active streams
- [ ] Show past streams (VOD)
- [ ] Show streamer bio and stats
- [ ] Follow/unfollow button
- [ ] Notification preferences

---

## Design & UX

- [ ] Design system (colors, typography, spacing)
- [ ] Dark mode support
- [ ] Responsive layout (desktop, tablet, mobile)
- [ ] Accessibility (WCAG 2.1)
- [ ] Loading states and skeletons
- [ ] Empty states
- [ ] Error states

---

## Frontend Architecture

- [ ] Choose frontend framework (React/Vue/Svelte)
- [ ] Set up build tooling (Vite/Webpack)
- [ ] Set up state management
- [ ] Set up routing
- [ ] Set up API client for QLive backend
- [ ] Set up WebSocket client for real-time updates
- [ ] Set up testing framework

### Components
- [ ] Player component
- [ ] Stream card component
- [ ] Streamer profile component
- [ ] Chat component
- [ ] Dashboard widgets

---

## Testing & QA

- [ ] Unit tests for components
- [ ] Integration tests for player
- [ ] End-to-end tests for broadcast flow
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Mobile testing (iOS, Android)
- [ ] Performance testing (page load, playback smoothness)

---

## Milestones

- [ ] **W1 — Player:** Basic live stream playback works in browser
- [ ] **W2 — Discovery:** Users can browse and find streams
- [ ] **W3 — Dashboard:** Streamers can manage broadcasts
- [ ] **W4 — Profiles:** Streamer profiles with live and VOD content
- [ ] **W5 — Polish:** Design system, mobile, accessibility

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| — | — | — |

---

*This document is a living artifact. Update it as the UI evolves.*