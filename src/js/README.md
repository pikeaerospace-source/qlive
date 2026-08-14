# QLive JavaScript/TypeScript Components

React + Vite + TypeScript web application for QLive.

## Overview

The Web UI provides four views:

- **Discover** — browse live, upcoming, and archived streams by category
- **Watch** — low-latency player (hls.js / native HLS) with live stats
- **Dashboard** — broadcaster controls and stream-health stats
- **Profile** — streamer profiles with their streams

All data flows through a swappable `Api` interface (`src/data/api.ts`). The
current implementation returns mock data, so the entire app runs offline — no
Qortal network, QDN, or live stream required. Swap the mock for a real QDN
client without touching the UI components.

## Development

```bash
# Install dependencies
npm install

# Vite dev server
npm run dev

# Type-check + production build
npm run build

# Preview the production build
npm run preview

# Type-check only
npm run typecheck

# Lint
npm run lint

# Unit tests (Vitest)
npm test

# End-to-end tests (Playwright) — first install browsers:
npx playwright install
npm run test:e2e
npm run test:e2e -- --project=firefox   # or --project=chromium
```

## Live stats

The Watch page subscribes to live stream statistics through the `Api`
interface. By default a local simulator runs (fully offline). To receive real
updates, point the WebSocket client at an endpoint before building:

```bash
VITE_STATS_WS_URL=wss://your-node/stats npm run build
```

## Structure

```
src/
  main.tsx            # entry point
  App.tsx             # routes
  index.css           # design system (dark theme)
  types.ts            # shared domain types (Stream, Streamer, …)
  data/
    api.ts            # data service abstraction (swappable backend)
    liveStats.ts      # live stats client (WebSocket + offline simulator)
    mock.ts           # mock streams & streamers
    api.test.ts
  components/
    Layout.tsx        # top bar + nav
    StreamCard.tsx    # stream card
    Player.tsx        # hls.js player (lazy-loaded)
    Stat.tsx          # stat block
    StatusBadge.tsx   # live/upcoming/replay badge
    StreamCard.test.tsx
  pages/
    DiscoveryPage.tsx # browse streams
    WatchPage.tsx     # watch a stream
    DashboardPage.tsx # broadcaster dashboard
    ProfilePage.tsx   # streamer profile
  test/
    setup.ts          # vitest + testing-library setup
```

## Dependencies

- Node.js 20+, TypeScript 5+, React 18, Vite 5
- See `package.json` for the full dependency list
