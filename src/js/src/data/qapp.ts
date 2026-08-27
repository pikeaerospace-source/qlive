/**
 * QLive — qapp-core (QDN) data adapter.
 *
 * Implements the `Api` interface from `api.ts` against the Qortal Data Network
 * via the same global `qortalRequest()` function that `qapp-core`'s hooks use
 * at runtime. `qapp-core` (the `qapp-core/` git submodule) is the canonical,
 * tested host of the `GET_USER_ACCOUNT` / `PUBLISH_QDN_RESOURCE` /
 * `FETCH_QDN_RESOURCE` / `SEARCH_QDN_RESOURCES` / `GET_NAME_DATA` actions and
 * the `JSON`/`VIDEO`/`THUMBNAIL` service vocabulary; we mirror only the small
 * slice we need here so this module compiles and is fully unit-testable
 * **offline** (no `qapp-core` dist / Qortal UI host required). When `qapp-core`
 * is wired in, swap the local type mirrors for `qapp-core`'s exported types and
 * drop the inline base64 decoder in favour of `base64ToObject`.
 */

import type { Api } from "./api";
// Type-only bridge to the qapp-core submodule: proves the vendored dependency
// (and its built `dist/index.d.ts`) resolve under the QLive Web UI. Erased at
// runtime, so the offline seam tests are unaffected. Replace the local mirrors
// below with qapp-core's exports as the integration deepens.
import type { QortalMetadata } from "qapp-core";
import type {
  Stream,
  Streamer,
  StreamStats,
  Resolution,
  Bitrate,
  StreamStatus,
} from "../types";

/* eslint-disable @typescript-eslint/no-explicit-any -- qortalRequest returns are opaque */

/** Re-export the qapp-core metadata type for consumers of the QDN adapter. */
export type { QortalMetadata };

/** Reserved QDN identifier prefix under which QLive publishes stream docs. */
export const QLIVE_STREAM_PREFIX = "QLIVE_STREAM_";

export const qliveStreamIdentifier = (streamId: string): string =>
  `${QLIVE_STREAM_PREFIX}${streamId}`;

/** Strip the prefix back to the QLive stream id. */
export const streamIdFromIdentifier = (
  identifier: string,
): string | undefined => {
  if (!identifier.startsWith(QLIVE_STREAM_PREFIX)) return undefined;
  return identifier.slice(QLIVE_STREAM_PREFIX.length);
};

/** The subset of qapp-core's `Service` used for QLive signaling. */
export type QortalService =
  "JSON" | "VIDEO" | "AUDIO" | "THUMBNAIL" | (string & {});

/** `QortalMetadata` is re-exported from the `qapp-core` submodule (see import above). */

/** Mirror of qapp-core's `QortalSearchParams` (only the fields QLive uses). */
export interface QortalSearchParams {
  service: QortalService;
  name?: string;
  identifier?: string;
  includemetadata?: boolean;
  limit?: number;
  offset?: number;
  mode?: "ALL" | "LATEST";
  reverse?: boolean;
  query?: string;
  keywords?: string[];
}

/** A single row returned by SEARCH_QDN_RESOURCES. */
export interface QortalSearchHit {
  name: string;
  identifier: string;
  service: QortalService;
  size: number;
  created: number;
  updated?: number;
  metadata?: { title?: string; description?: string; tags?: string[] };
}

/** The `qlive-stream` JSON document stored as QDN JSON resource data. */
export interface QLiveStreamDoc {
  version: number;
  publisher: string;
  title: string;
  description?: string;
  category: string;
  startedAt: number;
  status: StreamStatus;
  fragmentDurationMs: number;
  resolution: Resolution;
  bitrate: Bitrate;
  renditions?: number[];
  views?: number;
  encryption?: { enabled: boolean; keyId?: string };
  swarm?: { primaryTree: unknown[]; meshPeers: string[] };
  archive?: {
    status?: string;
    qdnResourceId?: string;
    qtubeManifestId?: string;
  };
  /** Live concurrent viewers (swarm-derived; filled on state change). */
  viewers?: number;
}

/** Options for the host-injected `qortalRequest` bridge. */
export type QortalRequestOptions = { action: string; [key: string]: unknown };

/** Minimal contract for a QDN / Qortal-API backend. Inject mock or real. */
export interface QortalBackend {
  qortalRequest(opts: QortalRequestOptions): Promise<any>;
}

const windowLike = () =>
  globalThis as unknown as {
    qortalRequest?: (o: QortalRequestOptions) => Promise<any>;
    qortalName?: string;
  };

/**
 * Backend that delegates to the `qortalRequest` function injected by the
 * Qortal UI host (the same global `qapp-core`'s hooks call). Throws a clear
 * error if the host is absent, so mis-wiring fails loudly instead of silently
 * returning empty data.
 */
export const createQortalBackend = (): QortalBackend => ({
  qortalRequest: (opts) => {
    const fn = windowLike().qortalRequest;
    if (!fn) {
      return Promise.reject(
        new Error(
          "qapp: host 'qortalRequest' not found — Qortal UI host not detected. " +
            "Run offline (mock) mode, or load within the Qortal UI.",
        ),
      );
    }
    return fn(opts);
  },
});

/**
 * Decode QDN resource data. `qapp-core` uses `base64ToObject` for `?encoding=base64`
 * responses and falls back to base64 → JSON. We replicate the JSON path here.
 * TODO(once wired): use qapp-core's exported `base64ToObject`.
 */
function decodeStreamDoc(raw: unknown): QLiveStreamDoc | null {
  if (!raw) return null;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as QLiveStreamDoc;
    } catch {
      return base64ToStreamDoc(raw);
    }
  }
  return raw as QLiveStreamDoc;
}

function base64ToStreamDoc(base64: string): QLiveStreamDoc | null {
  try {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const decoded = new TextDecoder().decode(bytes);
    return JSON.parse(decoded) as QLiveStreamDoc;
  } catch {
    return null;
  }
}

const QLIVE_STATUSES: StreamStatus[] = [
  "live",
  "announced",
  "ended",
  "archived",
];

/** Map a resolved QDN doc + metadata row to the Web UI's `Stream`. */
function toStream(
  identifier: string,
  doc: QLiveStreamDoc,
  hit?: QortalSearchHit,
): Stream {
  const streamId = streamIdFromIdentifier(identifier) ?? identifier;
  return {
    streamId,
    publisher: doc.publisher || hit?.name || "",
    title: doc.title ?? hit?.metadata?.title ?? "",
    description: doc.description ?? hit?.metadata?.description ?? "",
    category: doc.category,
    startedAt: doc.startedAt,
    status: doc.status,
    fragmentDurationMs: doc.fragmentDurationMs,
    resolution: doc.resolution,
    bitrate: doc.bitrate,
    viewers: doc.viewers ?? 0,
    thumbnail: thumbnailFromDoc(streamId, doc),
    playbackUrl: playbackUrlFromDoc(doc),
  };
}

function thumbnailFromDoc(
  streamId: string,
  doc: QLiveStreamDoc,
): string | undefined {
  // Archived streams can carry a Q-Tube manifest id; live preview thumbnails
  // come from the broadcaster, so leave undefined until the thumbnail QDN
  // resource (Service.THUMBNAIL) is wired in here.
  if (doc.archive?.qtubeManifestId)
    return `/arbitrary/THUMBNAIL/${encodeURIComponent(doc.publisher)}/${streamId}`;
  return undefined;
}

function playbackUrlFromDoc(doc: QLiveStreamDoc): string | undefined {
  // Archived/VOD playback is served from QDN once committed by the VOD engine.
  return doc.archive?.status === "archived" && doc.archive.qdnResourceId
    ? `/arbitrary/VIDEO/${encodeURIComponent(doc.publisher)}/${doc.archive.qdnResourceId}`
    : undefined;
}

/** Stats are a transport-layer (swarm/WebSocket) concern, not QDN. Passed via StatsDeps. */
export interface StatsDeps {
  getStats(streamId: string): Promise<StreamStats>;
  subscribe(
    streamId: string,
    onUpdate: (stats: StreamStats) => void,
  ): () => void;
}

const noopStats: StatsDeps = {
  getStats: () =>
    Promise.resolve({
      viewers: 0,
      bandwidthKbps: 0,
      bufferState: "filling",
      chunksProduced: 0,
      retransmissions: 0,
    }),
  subscribe: () => () => {
    /* no-op */
  },
};

/**
 * Build an `Api` backed by a QDN/Qortal host. `backend` is injectable so tests
 * never touch the real (or absent) Qortal host. `stats` defaults to a no-op:
 * real viewer/bandwidth stats come from the live swarm socket and must be
 * injected once that transport is wired.
 */
export const createQappApi = (
  backend: QortalBackend,
  stats: StatsDeps = noopStats,
): Api => {
  const searchStreams = async (
    params: QortalSearchParams,
  ): Promise<Stream[]> => {
    const hits: QortalSearchHit[] = await backend.qortalRequest({
      action: "SEARCH_QDN_RESOURCES",
      ...params,
    });
    if (!Array.isArray(hits)) return [];
    const results: Stream[] = [];
    for (const hit of hits) {
      if (!hit.identifier.startsWith(QLIVE_STREAM_PREFIX)) continue;
      const raw: unknown = await backend.qortalRequest({
        action: "FETCH_QDN_RESOURCE",
        service: hit.service,
        name: hit.name,
        identifier: hit.identifier,
        encoding: "base64",
      });
      const doc = decodeStreamDoc(raw);
      if (!doc || !QLIVE_STATUSES.includes(doc.status)) continue;
      results.push(toStream(hit.identifier, doc, hit));
    }
    return results;
  };

  return {
    listStreams: () =>
      searchStreams({
        service: "JSON",
        query: QLIVE_STREAM_PREFIX,
        includemetadata: true,
        limit: 100,
        mode: "ALL",
        reverse: true,
      }),

    getStream: async (streamId: string) => {
      const identifier = qliveStreamIdentifier(streamId);
      // Try the publisher's Qortal Name. The mock has no authenticated name, so
      // fall back to a search-scoped fetch when the host name is unknown (the
      // real QDN resource is namespaced under the publisher's Name).
      const name = windowLike().qortalName;
      const tryFetch = (n: string) =>
        backend.qortalRequest({
          action: "FETCH_QDN_RESOURCE",
          service: "JSON",
          name: n,
          identifier,
          encoding: "base64",
        }) as Promise<any>;
      const raw = name
        ? await tryFetch(name).catch(() => undefined)
        : undefined;
      const doc = decodeStreamDoc(raw);
      if (!doc) {
        const [hit] = await searchStreams({
          service: "JSON",
          identifier,
          includemetadata: true,
          limit: 1,
        });
        return hit;
      }
      return toStream(identifier, doc);
    },

    getStreamer: async (name: string) => {
      const nameData: any = await backend.qortalRequest({
        action: "GET_NAME_DATA",
        name,
      });
      if (!nameData) return undefined;
      const streamer: Streamer = {
        name: nameData.name,
        bio: nameData.description ?? nameData.group ?? "",
        followers:
          typeof nameData.followers === "number" ? nameData.followers : 0, // TODO: social followers are off-chain (QLive social layer)
        verified:
          typeof nameData.verified === "boolean" ? nameData.verified : false,
      };
      return streamer;
    },

    getStreamerStreams: (name: string) =>
      searchStreams({
        service: "JSON",
        name,
        includemetadata: true,
        limit: 100,
        mode: "ALL",
        reverse: true,
      }),

    getStreamStats: stats.getStats,
    subscribeStats: stats.subscribe,
  };
};

/** Default QDN-backed api bound to the host `qortalRequest` (no-op stats). */
export const qappApi: Api = createQappApi(createQortalBackend());

/* eslint-enable @typescript-eslint/no-explicit-any */
