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
  createStreamPublisher,
  QLIVE_STREAM_PREFIX,
  streamToPublication,
} from "./qapp";
import type { Stream, StreamStats } from "../types";

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

  it("maps the archive reference of a completed stream", async () => {
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "bob",
            identifier: `${QLIVE_STREAM_PREFIX}arch1`,
            service: "JSON",
            size: 12,
            created: 1,
          },
        ]),
      FETCH_QDN_RESOURCE: () =>
        Promise.resolve({
          ...DOC,
          publisher: "bob",
          status: "archived",
          archive: {
            status: "archived",
            qdnResourceId: "qlive-archive-arch1",
            qtubeManifestId: "qlive-manifest-arch1",
          },
        }),
    });

    const api = createQappApi(backend);
    const [stream] = await api.listStreams();

    expect(stream.archive).toEqual({
      qdnResourceId: "qlive-archive-arch1",
      qtubeManifestId: "qlive-manifest-arch1",
      status: "archived",
    });
    expect(stream.playbackUrl).toBe(
      "/arbitrary/VIDEO/bob/qlive-archive-arch1",
    );
  });

  it("treats an unrecognised archive status as pending", async () => {
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "bob",
            identifier: `${QLIVE_STREAM_PREFIX}arch2`,
            service: "JSON",
            size: 12,
            created: 1,
          },
        ]),
      FETCH_QDN_RESOURCE: () =>
        Promise.resolve({
          ...DOC,
          status: "archived",
          archive: { status: "finishing", qdnResourceId: "res-2" },
        }),
    });

    const api = createQappApi(backend);
    const [stream] = await api.listStreams();
    expect(stream.archive?.status).toBe("pending");
    // Not advertised as playable until confirmed archived.
    expect(stream.playbackUrl).toBeUndefined();
  });

  it("leaves archive undefined when the doc references no archive", async () => {
    const backend = makeBackend({
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "alice",
            identifier: `${QLIVE_STREAM_PREFIX}live1`,
            service: "JSON",
            size: 3,
            created: 1,
          },
        ]),
      FETCH_QDN_RESOURCE: () => Promise.resolve(DOC),
    });

    const api = createQappApi(backend);
    const [stream] = await api.listStreams();
    expect(stream.archive).toBeUndefined();
  });
});

const PUBLICATION = {
  streamId: "abc123",
  title: "Speedrunning Hollow Knight",
  description: "PB attempt",
  category: "gaming",
  status: "announced" as const,
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 60 },
  bitrate: { video: 6_000_000, audio: 128_000 },
  startedAt: 1_700_000_000_000,
};

type RecordedCall = { action: string; [k: string]: unknown };

const recordingBackend = (calls: RecordedCall[]) => ({
  qortalRequest: (opts: RecordedCall) => {
    calls.push(opts);
    return Promise.resolve({ signature: "sig" });
  },
});

describe("qapp stream publisher (QDN write path)", () => {
  it("publishes the qlive-stream doc under the authenticated name", async () => {
    const calls: RecordedCall[] = [];
    const publisher = createStreamPublisher(recordingBackend(calls), {
      name: "alice",
    });

    const result = await publisher.publishStream(PUBLICATION);

    expect(result.identifier).toBe(`${QLIVE_STREAM_PREFIX}abc123`);
    expect(result.service).toBe("JSON");
    expect(result.doc).toEqual(
      expect.objectContaining({
        type: "qlive-stream",
        version: 1,
        publisher: "alice",
        title: PUBLICATION.title,
        status: "announced",
        startedAt: PUBLICATION.startedAt,
        viewers: 0,
      }),
    );

    expect(calls).toHaveLength(1);
    const call = calls[0];
    expect(call.action).toBe("PUBLISH_QDN_RESOURCE");
    expect(call.service).toBe("JSON");
    expect(call.name).toBe("alice");
    expect(call.identifier).toBe(`${QLIVE_STREAM_PREFIX}abc123`);
    expect(call.title).toBe(PUBLICATION.title);
    expect(call.category).toBe("gaming");
    expect(call.tags).toEqual(["qlive", "gaming", "announced"]);
    // The base64 payload decodes back to the document that was published.
    expect(JSON.parse(atob(String(call.data64)))).toEqual(result.doc);
  });

  it("uses the host-injected Qortal Name when no name is given", async () => {
    setGlobal("qortalName", "carol");
    try {
      const publisher = createStreamPublisher(recordingBackend([]));
      const result = await publisher.publishStream(PUBLICATION);
      expect(result.name).toBe("carol");
      expect(result.doc.publisher).toBe("carol");
    } finally {
      unsetGlobal("qortalName");
    }
  });

  it("fails loudly when no Qortal Name is available", async () => {
    unsetGlobal("qortalName");
    const publisher = createStreamPublisher(makeBackend({}));
    await expect(publisher.publishStream(PUBLICATION)).rejects.toThrow(
      /authenticated Qortal Name/,
    );
  });

  it("requires a streamId", async () => {
    const publisher = createStreamPublisher(makeBackend({}), { name: "alice" });
    await expect(
      publisher.publishStream({ ...PUBLICATION, streamId: "  " }),
    ).rejects.toThrow(/requires a streamId/);
  });

  it("tombstones the stream doc on unpublish", async () => {
    const calls: RecordedCall[] = [];
    await createStreamPublisher(recordingBackend(calls), {
      name: "alice",
    }).unpublishStream("abc123");

    expect(calls).toHaveLength(1);
    expect(calls[0].action).toBe("PUBLISH_QDN_RESOURCE");
    expect(calls[0].identifier).toBe(`${QLIVE_STREAM_PREFIX}abc123`);
    expect(calls[0].data64).toBe("RA==");
  });

  it("round-trips a published doc back into a Stream", async () => {
    const published: string[] = [];
    const backend = makeBackend({
      PUBLISH_QDN_RESOURCE: (opts) => {
        published.push(String(opts.data64));
        return Promise.resolve({ signature: "sig" });
      },
      SEARCH_QDN_RESOURCES: () =>
        Promise.resolve([
          {
            name: "alice",
            identifier: `${QLIVE_STREAM_PREFIX}abc123`,
            service: "JSON",
            size: 40,
            created: 1,
          },
        ]),
      FETCH_QDN_RESOURCE: () => Promise.resolve(published[0]),
    });

    const { doc } = await createStreamPublisher(backend, {
      name: "alice",
    }).publishStream({
      ...PUBLICATION,
      status: "archived",
      archive: { status: "archived", qdnResourceId: "qlive-archive-abc123" },
    });

    const [stream] = await createQappApi(backend).listStreams();

    expect(doc.publisher).toBe("alice");
    expect(stream).toEqual(
      expect.objectContaining({
        streamId: "abc123",
        publisher: "alice",
        title: PUBLICATION.title,
        category: "gaming",
        status: "archived",
        resolution: PUBLICATION.resolution,
        bitrate: PUBLICATION.bitrate,
      }),
    );
    expect(stream.archive?.status).toBe("archived");
    expect(stream.playbackUrl).toBe(
      "/arbitrary/VIDEO/alice/qlive-archive-abc123",
    );
  });

  it("derives a publication from an existing stream", () => {
    const stream: Stream = {
      streamId: "s1",
      publisher: "alice",
      title: "Test stream",
      description: "",
      category: "gaming",
      startedAt: 10,
      status: "live",
      fragmentDurationMs: 1000,
      resolution: { width: 1280, height: 720, fps: 30 },
      bitrate: { video: 2_500_000, audio: 128_000 },
      viewers: 7,
      archive: { qdnResourceId: "res-1", status: "archived", durationMs: 1000 },
    };

    const pub = streamToPublication(stream, { status: "ended" });

    expect(pub).toEqual(
      expect.objectContaining({
        streamId: "s1",
        status: "ended",
        viewers: 7,
        startedAt: 10,
        archive: { status: "archived", qdnResourceId: "res-1" },
      }),
    );
  });
});
