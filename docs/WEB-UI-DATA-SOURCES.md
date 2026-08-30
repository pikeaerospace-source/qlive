# Web UI — Data Sources: Offline (Mock) vs. Local Qortal Node

**Status:** Complete (`[x]`) — reference for operating the Web UI in either mode.

**Related:** [TODO-QAPP-CORE.md](../TODO-QAPP-CORE.md), `src/js/src/data/api.ts`,
`src/js/src/data/qapp.ts`, `src/js/src/data/mock.ts`, `qapp-core/` (submodule).

The QLive Web UI is a **single codebase with two data sources** behind one
interface:

1. **Offline / mock** — canned data served entirely in-browser. No Qortal node,
   no network, no `qapp-core` runtime. This is the default for local dev, CI,
   and unit tests.
2. **QDN-backed** — real stream metadata and VOD resources served from the
   Qortal Data Network via the same global `qortalRequest()` bridge that the
   `qapp-core` submodule's hooks call.

Both are exposed through the same `Api` interface (`src/js/src/data/api.ts`),
so UI components never know (or care) which backend is active.

---

## The seam: `selectApi()`

`src/js/src/data/api.ts` exports a single runtime toggle:

```ts
export const selectApi = (): Api =>
  typeof (globalThis as { qortalRequest?: unknown }).qortalRequest ===
  "function"
    ? qappApi        // QDN-backed (run inside a Qortal UI host)
    : api;           // offline mock (default)
```

The decision is purely a **host-presence check**: if a Qortal UI host has
injected `window.qortalRequest` (a function), the app talks to QDN; otherwise
it falls back to the in-memory mock. There is no config flag to flip and no
build-time switch — the environment decides.

| Environment | `window.qortalRequest` | `selectApi()` → | Data |
| --- | --- | --- | --- |
| `npm run dev` (standalone Vite) | absent | `api` (mock) | `mock.ts` |
| Vitest (jsdom, offline) | absent / injected fake in tests | `api` or `qappApi` | mock or fake `QortalBackend` |
| Inside the Qortal UI (Q-App) | present | `qappApi` | QDN (`SEARCH_QDN_RESOURCES`, `FETCH_QDN_RESOURCE`, `GET_NAME_DATA`, …) |

---

## Mode 1 — Offline / mock (no Qortal node, no internet)

The default. No Qortal Core, no QDN, no `qapp-core` build artifacts, no
`window.qortalRequest`.

### Run

```bash
git submodule update --init --recursive   # fetch qapp-core (needed for the build/typechain, not for the mock runtime)
cd src/js
npm install
npm run dev                               # http://localhost:5173 — mock data everywhere
```

Everything renders from `src/js/src/data/mock.ts`: the Discovery page, Watch
page, Dashboard, and Profile views all populate with canned stream/streamer
records. Live stats come from the offline `StatsClient` simulator in
`src/js/src/data/liveStats.ts`. No ports other than the Vite dev server are
required.

### Test (also fully offline)

```bash
cd src/js
npm test                                  # Vitest: unit + data-seam tests, no network/host
npm run build                             # tsc --noEmit + vite build (type-checks against qapp-core types)
```

The adapter tests in `src/js/src/data/qapp.test.ts` inject a fake
`QortalBackend` so the QDN code paths are exercised **without** a real Qortal
host or node — see `makeBackend(...)` and `createQappApi(backend)`.

> **Note:** although offline mode never *uses* `qapp-core` at runtime,
> typechecking and `npm run build` resolve `qapp-core`'s exported types, so the
> submodule must be present and built once (`cd qapp-core && npm install && npm
> run build`) as part of the toolchain.

---

## Mode 2 — Pointing at a local Qortal node (QDN-backed)

Here the Web UI reads real stream metadata / VOD resources published by QLive
broadcasters. The adapter (`src/js/src/data/qapp.ts`) drives QDN through the
same actions `qapp-core` uses:

| Adapter call | `qortalRequest` action |
| --- | --- |
| `listStreams()` | `SEARCH_QDN_RESOURCES` (service `JSON`, identifier prefix `QLIVE_STREAM_`) then `FETCH_QDN_RESOURCE` per hit |
| `getStream(id)` | `FETCH_QDN_RESOURCE` (namespaced under publisher Name; falls back to search-scoped fetch) |
| `getStreamer(name)` | `GET_NAME_DATA` |
| `getStreamerStreams(name)` | `SEARCH_QDN_RESOURCES` (service `JSON`, scoped by `name`) |

### How `qortalRequest` gets injected

`window.qortalRequest` is the API bridge provided by the **Qortal UI host**
(the wrapper that loads Q-App QApps). It is not present by default in a bare
Vite dev server. There are two supported ways to get a QDN-backed UI:

**A. Run within the Qortal UI (recommended, matches Q-App deployment).**
Build the QLive Web UI and load it as a Q-App inside a Qortal UI instance
pointing at your local Qortal Core node. The host injects `qortalRequest`,
`selectApi()` detects it, and the app switches to QDN automatically. This also
gives you `useAuth`/`GlobalProvider` (deferred until the Q3 integration) and
`window.qortalName` (used by `getStream` for direct per-Name fetches).

**B. Shim `qortalRequest` in the standalone Vite dev server (fast local loop).**
For development against real QDN data, inject a small polyfill before the app
boots that forwards `qortalRequest` actions to your local Qortal Core node's
REST API (default `http://localhost:12391`, loopback). `selectApi()` will then
resolve to `qappApi`. A minimal sketch (`qortalRequestShim.ts`):

```ts
// Injects `window.qortalRequest` into the Vite dev server so the QLive UI
// talks to a local Qortal Core node. Dev-only shim — in production the Qortal
// UI host injects qortalRequest for us.
const CORE = "http://localhost:12391";

(globalThis as any).qortalRequest = async (opts: any) => {
  switch (opts.action) {
    case "GET_USER_ACCOUNT": {
      const r = await fetch(`${CORE}/addresses/` + /* selected address */ "");
      return r.json();
    }
    case "SEARCH_QDN_RESOURCES": {
      const q = new URLSearchParams({
        service: opts.service,
        ...(opts.name ? { name: opts.name } : {}),
        ...(opts.identifier ? { identifier: opts.identifier } : {}),
        ...(opts.limit ? { limit: String(opts.limit) } : {}),
        ...(opts.includemetadata ? { includemetadata: "true" } : {}),
      }).toString();
      const r = await fetch(`${CORE}/arbitrary/resources/search?${q}`);
      return r.json();
    }
    case "FETCH_QDN_RESOURCE": {
      const url = `${CORE}/arbitrary/${opts.service}/${encodeURIComponent(opts.name)}/${encodeURIComponent(opts.identifier)}${opts.encoding === "base64" ? "?encoding=base64" : ""}`;
      const r = await fetch(url);
      return r.json();
    }
    case "GET_NAME_DATA": {
      const r = await fetch(`${CORE}/names/${encodeURIComponent(opts.name)}`);
      return r.json();
    }
    default:
      throw new Error(`unhandled qortalRequest action: ${opts.action}`);
  }
};
```

> ⚠️ **Verify before relying on it.** The exact Qortal Core REST paths, query
> parameters, and response shapes must be confirmed against the node you target
> — see [QORTAL-CORE-API.md](QORTAL-CORE-API.md) (Verification section). Once a
> real host is wired, prefer the injected `qortalRequest` over the shim.

### The `QortalBackend` injectable (for tests & custom endpoints)

`qapp.ts` models the node as a tiny interface so anything that speaks
`qortalRequest` can back the adapter:

```ts
export interface QortalBackend {
  qortalRequest(opts: QortalRequestOptions): Promise<any>;
}
```

- **Default** — `createQortalBackend()` delegates to the host-injected
  `window.qortalRequest`, and rejects loudly if the host is absent (so
  mis-wiring fails instead of silently returning empty data).
- **Tests** — `qapp.test.ts` passes a fake backend, so the QDN mapping is
  exercisable with zero infrastructure.
- **Custom nodes** — implement a `QortalBackend` that forwards to any
  Qortal-compatible endpoint and pass it to `createQappApi(backend)`.

---

## Choosing a mode — quick reference

| You want to… | Do this |
| --- | --- |
| Develop the UI / mock data quickly, no node | `cd src/js && npm run dev` (mock is default) |
| Run the unit/data-seam tests offline | `cd src/js && npm test` |
| See real QDN data against a **local** node | Load the app inside a Qortal UI, or inject the dev shim above |
| Deploy as a Q-App on Qortal | Build with `npm run build`; the host injects `qortalRequest`, QDN is used automatically |

---

## Current status & limitations

- **Default mode is offline/mock.** The `qapp-core` integration seam
  (`selectApi`, `qapp.ts` adapter, tests) is complete and offline-verified;
  real-time auth + live signaling via `GlobalProvider` is deferred to the Q3
  milestone (see [TODO-QAPP-CORE.md](../TODO-QAPP-CORE.md)).
- **Stats are still mock/transport-layer.** `getStreamStats` / `subscribeStats`
  in the QDN adapter default to a no-op until the live swarm/WebSocket socket
  is wired; real viewer/bandwidth data is not (yet) available from QDN.
- **Publish (write path) is not wired in the UI.** The QDN adapter currently
  only *reads* QDN (`SEARCH`/`FETCH`/`GET_NAME_DATA`); broadcasting metadata
  via `PUBLISH_QDN_RESOURCE` is part of the Q3 signaling work.

---

*This document is a living artifact — update it as the QDN integration deepens.*