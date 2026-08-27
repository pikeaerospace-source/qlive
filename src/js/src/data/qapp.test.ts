/**
 * Tests for the qapp-core (QDN) data adapter.
 *
 * A fake `QortalBackend` is injected so these run **fully offline** — no
 * `qapp-core` dist, no Qortal UI host, no network. They assert the QLive↔QDN
 * mapping (prefix filtering, status filtering, resource → Stream, name-data →
 * Streamer, stats delegation, host-absent error).
 */

import { describe, expect, it, vi } from "vitest";

import {
  createQappApi,
  createQortalBackend,
  QLIVE_STREAM_PREFIX,
} from "./qapp";
import type { StreamStats } from "../types";

const DOC = {
  version: 1,
  publisher: "alice",
  title: "Speedrunning Hollow Knight — Any%",
  description: "Attempting a new personal best.",
  category: "gaming",
  startedAt: 1_000,
  status: "live" as const,
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 60 },
  bitrate: { video: 6_000_000, audio: 128_000 },
  viewers: 312,
};

const liveStats: StreamStats = {
  viewers: 312,
  bandwidthKbps: 5890,
  bufferState: "healthy",
  chunksProduced: 1234,
  retransmissions: 7,
};

type Handlers = Record<
  string,
  (opts: { action: string; [k: string]: unknown }) => Promise<any>
>;

const makeBackend = (handlers: Handlers) => ({
  qortalRequest: (opts: { action: string; [k: string]: unknown }) => {
    const h = handlers[opts.action];
    if (!h)
      return Promise.reject(new Error(`unhandled action: ${opts.action}`));
    return h(opts);
  },
});

const setGlobal = (key: string, value: unknown) => {
  (globalThis as Record<string, unknown>)[key] = value;
};
const unsetGlobal = (key: string) => {
  delete (globalThis as Record<string, unknown>)[key];
};

describe("qapp adapter (QDN-backed Api)", () => {
  it("maps QDN search hits to streams and filters by prefix + lifecycle", async () => {
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "alice",
            identifier: `${QLIVE_STREAM_PREFIX}foo1`,
            service: "JSON",
            size: 10,
            created: 1,
            metadata: { title: "Speedrunning Hollow Knight" },
          },
          {
            name: "bob",
            identifier: "SOME_OTHER_RESOURCE",
            service: "JSON",
            size: 5,
            created: 2,
          },
          {
            name: "carol",
            identifier: `${QLIVE_STREAM_PREFIX}foo2`,
            service: "JSON",
            size: 8,
            created: 3,
          },
        ]),
      FETCH_QDN_RESOURCE: (opts) =>
        Promise.resolve({
          ...DOC,
          status:
            opts.identifier === `${QLIVE_STREAM_PREFIX}foo1` ? "live" : "ended",
        }),
    });

    const api = createQappApi(backend);
    const streams = await api.listStreams();

    // "SOME_OTHER_RESOURCE" is filtered out (prefix); both live & ended are valid statuses
    expect(streams).toHaveLength(2);
    const live = streams.find((s) => s.streamId === "foo1");
    expect(live).toEqual(
      expect.objectContaining({
        streamId: "foo1",
        publisher: "alice",
        title: "Speedrunning Hollow Knight — Any%",
        category: "gaming",
        status: "live",
        viewers: 312,
        fragmentDurationMs: 1000,
        resolution: { width: 1920, height: 1080, fps: 60 },
        bitrate: { video: 6_000_000, audio: 128_000 },
      }),
    );
  });

  it("fetches a single stream by id via FETCH_QDN_RESOURCE", async () => {
    setGlobal("qortalName", "alice");
    let fetchOpts: { action: string; [k: string]: unknown } | undefined;
    const backend = makeBackend({
      FETCH_QDN_RESOURCE: (opts) => {
        fetchOpts = opts;
        return Promise.resolve(DOC);
      },
    });
    const api = createQappApi(backend);

    const stream = await api.getStream("abc123");
    unsetGlobal("qortalName");

    expect(stream).toMatchObject({
      streamId: "abc123",
      publisher: "alice",
      title: DOC.title,
    });
    expect(fetchOpts?.action).toBe("FETCH_QDN_RESOURCE");
    expect(fetchOpts?.identifier).toBe(`${QLIVE_STREAM_PREFIX}abc123`);
    expect(fetchOpts?.name).toBe("alice");
  });

  it("falls back to search when the host name / resource is missing", async () => {
    unsetGlobal("qortalName");
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "alice",
            identifier: `${QLIVE_STREAM_PREFIX}xyz`,
            service: "JSON",
            size: 9,
            created: 0,
          },
        ]),
      // Direct (host-name) fetch would 404; once the search resolves the
      // publisher name "alice", the per-hit fetch returns the doc.
      FETCH_QDN_RESOURCE: (opts) =>
        Promise.resolve(
          opts.name === "alice" ? { ...DOC, startedAt: 2_000 } : null,
        ),
    });
    const api = createQappApi(backend);
    const stream = await api.getStream("xyz");
    expect(stream).toEqual(
      expect.objectContaining({ streamId: "xyz", publisher: "alice" }),
    );
  });

  it("maps Qortal name data to a Streamer", async () => {
    const backend = makeBackend({
      GET_NAME_DATA: () =>
        Promise.resolve({
          name: "alice",
          description: "Indie game dev & speedrunner.",
          followers: 1204,
          verified: true,
        }),
    });
    const api = createQappApi(backend);
    await expect(api.getStreamer("alice")).resolves.toEqual({
      name: "alice",
      bio: "Indie game dev & speedrunner.",
      followers: 1204,
      verified: true,
    });
  });

  it("returns undefined for an unknown streamer", async () => {
    const backend = makeBackend({ GET_NAME_DATA: () => Promise.resolve(null) });
    const api = createQappApi(backend);
    await expect(api.getStreamer("ghost")).resolves.toBeUndefined();
  });

  it("returns streams scoped to a publisher's name", async () => {
    let searchedName: string | undefined;
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: (opts) => {
        searchedName = String(opts.name);
        return Promise.resolve([
          {
            name: "alice",
            identifier: `${QLIVE_STREAM_PREFIX}a1`,
            service: "JSON",
            size: 1,
            created: 0,
          },
        ]);
      },
      FETCH_QDN_RESOURCE: () => Promise.resolve(DOC),
    });
    const api = createQappApi(backend);
    const streams = await api.getStreamerStreams("alice");
    expect(searchedName).toBe("alice");
    expect(streams).toHaveLength(1);
    expect(streams[0].publisher).toBe("alice");
  });

  it("delegates stats to the injected StatsDeps", async () => {
    const getStats = vi.fn().mockResolvedValue(liveStats);
    const subscribe = vi.fn();
    const backend = makeBackend({});
    const api = createQappApi(backend, { getStats, subscribe });

    await expect(api.getStreamStats("foo1")).resolves.toEqual(liveStats);
    expect(getStats).toHaveBeenCalledWith("foo1");

    const off = api.subscribeStats("foo1", () => {});
    expect(subscribe).toHaveBeenCalledWith("foo1", expect.any(Function));
    expect(off).toBeUndefined();
  });

  it("createQortalBackend rejects when the host global is absent", async () => {
    unsetGlobal("qortalRequest");
    const backend = createQortalBackend();
    await expect(
      backend.qortalRequest({ action: "GET_USER_ACCOUNT" }),
    ).rejects.toThrow(/host 'qortalRequest' not found/);
  });
});
