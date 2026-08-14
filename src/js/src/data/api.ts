import type { Stream, Streamer, StreamStats } from "../types";
import { mockStreams, mockStreamers } from "./mock";

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
}

function delay<T>(value: T, ms = 30): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
}

export const api: Api = {
  listStreams: () => delay([...mockStreams]),
  getStream: (streamId) =>
    delay(mockStreams.find((s) => s.streamId === streamId)),
  getStreamer: (name) =>
    delay(mockStreamers.find((s) => s.name === name)),
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
};
