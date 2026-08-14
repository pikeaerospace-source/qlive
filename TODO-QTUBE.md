# QLive — Q-Tube Integration TODO

Tracking tasks for integrating QLive with Q-Tube for live streaming and VOD replay.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Complete

---

## Overview

Q-Tube is Qortal's decentralized video platform. QLive integration enables:
1. **Live streaming** — Q-Tube users can discover and watch live streams
2. **VOD replay** — Completed live streams automatically become Q-Tube videos
3. **Streamer profiles** — Qortal Names show both live and archived content

---

## Manifest Format Compatibility

- [ ] Coordinate with Q-Tube team on manifest format compatibility
- [ ] Review Q-Tube's existing manifest schema for VOD videos
- [ ] Map QLive's `QTubeManifest` to Q-Tube's expected format
- [ ] Define the live stream metadata schema for Q-Tube discovery
- [ ] Document the manifest mapping in `docs/qtube-integration.md`
- [ ] Create a compatibility test suite against Q-Tube's schema

### Open Questions
- Does Q-Tube use a specific manifest version we need to target?
- How does Q-Tube handle chunked video (multiple QDN resources)?
- What metadata fields does Q-Tube require vs. optional?

---

## Live Player Embedding

- [ ] Embed QLive player in Q-Tube
- [ ] Create a QLive player component for Q-Tube's frontend
- [ ] Implement live stream discovery in Q-Tube's UI
- [ ] Add "Live Now" section on Q-Tube homepage
- [ ] Add live badge to streamer profiles
- [ ] Implement stream status indicators (live, ended, archived)
- [ ] Handle stream interruptions gracefully in the player

### Player Features
- [ ] Low-latency playback (sub-1s target)
- [ ] Adaptive bitrate switching
- [ ] Buffer health indicator
- [ ] Retransmission status display
- [ ] Chat integration (optional)

---

## VOD Replay

- [ ] Implement "Watch Replay" link on live stream pages
- [ ] Implement live → VOD transition UX (no re-encoding)
- [ ] Auto-publish completed streams to Q-Tube
- [ ] Show "Replay Available" after stream ends
- [ ] Link live stream page to archived VOD
- [ ] Handle partial archives (interrupted streams)

### VOD Pipeline
- [ ] Verify QDN chunk commit works with Q-Tube's storage
- [ ] Test hash chain integrity across Q-Tube's retrieval
- [ ] Implement archive status tracking in Q-Tube UI
- [ ] Add "Archiving..." progress indicator

---

## Streamer Profiles

- [ ] Streamer profile integration (Qortal Name → live streams)
- [ ] Show active streams on Qortal Name profiles
- [ ] Show past streams (VOD) on profiles
- [ ] Add "Go Live" button for verified streamers
- [ ] Display streamer stats (viewer count, total streams, followers)

---

## Monetization Integration

- [ ] QORT tipping in Q-Tube player
- [ ] Pay-Per-View streams in Q-Tube
- [ ] Subscriber-only streams
- [ ] Donation button on streamer profiles
- [ ] Revenue dashboard for streamers

---

## Testing & QA

- [ ] Test live stream playback in Q-Tube
- [ ] Test VOD replay after stream ends
- [ ] Test interrupted stream handling
- [ ] Test multiple concurrent streams
- [ ] Test mobile browser playback
- [ ] Test low-bandwidth scenarios

---

## Milestones

- [ ] **Q1 — Manifest compatibility:** Q-Tube can read QLive manifests
- [ ] **Q2 — Live playback:** Q-Tube can play live streams
- [ ] **Q3 — VOD replay:** Completed streams appear as Q-Tube videos
- [ ] **Q4 — Full integration:** Live section, profiles, monetization

---

## Notes & Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| — | — | — |

---

*This document is a living artifact. Update it as the integration evolves.*