# QLive JavaScript/TypeScript Components

JavaScript/TypeScript components for the QLive decentralized live-streaming protocol.

## Planned Components

| Component | Status | Description |
| --- | --- | --- |
| `player/` | Planned | Web player (CMAF/HLS playback, low-latency mode) |
| `broadcaster/` | Planned | Broadcaster CLI and web UI |
| `viewer/` | Planned | Viewer CLI and web UI |
| `webrtc/` | Planned | WebRTC data channel transport |
| `cli/` | Planned | `qlive broadcast` / `qlive watch` CLI tools |

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Type-check
npm run typecheck

# Lint
npm run lint

# Test
npm test
```

## Dependencies

- Node.js 18+
- TypeScript 5+
- See `package.json` for full dependency list