import type { Stream, Streamer, StreamStats } from "../types";
import { createStatsClient, type StatsClient } from "./liveStats";
import { mockStreams, mockStreamers } from "./mock";
import { qappApi } from "./qapp";

/**
 * Data service abstraction for the QLive Web UI.
 *
 * The `api` object is the single point of data access. In offline/mock mode it
 * returns canned data; in production it would query QDN and subscribe to
 * WebSocket updates. Components depend on `Api` only, never on the mock
 * directly, so the backend can be swapped without touching the UI.
 */
export interface Api {
  listStreams(): Promise<Stream[]>;
  getStream(streamId: string): Promise<Stream | undefined>;
  getStreamer(name: string): Promise<Streamer | undefined>;
  getStreamerStreams(name: string): Promise<Stream[]>;
  getStreamStats(streamId: string): Promise<StreamStats>;
  /** Subscribe to live stats. Returns an unsubscribe function. */
  subscribeStats(
    streamId: string,
    onUpdate: (stats: StreamStats) => void,
  ): () => void;
}

function delay<T>(value: T, ms = 30): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
}

let statsClient: StatsClient | undefined;

function getStatsClient(): StatsClient {
  if (!statsClient) {
    statsClient = createStatsClient(mockStreams);
  }
  return statsClient;
}

export const api: Api = {
  listStreams: () => delay([...mockStreams]),
  getStream: (streamId) =>
    delay(mockStreams.find((s) => s.streamId === streamId)),
  getStreamer: (name) => delay(mockStreamers.find((s) => s.name === name)),
  getStreamerStreams: (name) =>
    delay(mockStreams.filter((s) => s.publisher === name)),
  getStreamStats: (streamId) => {
    const stream = mockStreams.find((s) => s.streamId === streamId);
    return delay<StreamStats>({
      viewers: stream?.viewers ?? 0,
      bandwidthKbps: stream ? Math.round(stream.bitrate.video / 1000) : 0,
      bufferState: "healthy",
      chunksProduced: 1234,
      retransmissions: 7,
    });
  },
  subscribeStats: (streamId, onUpdate) =>
    getStatsClient().subscribe(streamId, onUpdate),
};

/**
 * Re-export the qapp-core-backed implementation so callers can opt into real
 * QDN access. `Api` remains the only interface components depend on.
 */
export { createQappApi, createQortalBackend } from "./qapp";

/**
 * Seam toggle: prefer the QDN-backed api when the Qortal UI host has injected
 * `qortalRequest` (i.e. running inside the Qortal UI / qapp-core wired up);
 * otherwise fall back to the offline mock. Components should consume
 * `selectApi()` instead of importing `api` directly once wired.
 */
export const selectApi = (): Api =>
  typeof (globalThis as { qortalRequest?: unknown }).qortalRequest ===
  "function"
    ? qappApi
    : api;
