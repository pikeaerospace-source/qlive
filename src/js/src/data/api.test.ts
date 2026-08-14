import { describe, expect, it } from "vitest";
import type { StreamStats } from "../types";
import { api } from "./api";

describe("api (mock)", () => {
  it("lists streams", async () => {
    const streams = await api.listStreams();
    expect(streams.length).toBeGreaterThan(0);
    expect(streams.some((s) => s.status === "live")).toBe(true);
  });

  it("finds a stream by id", async () => {
    const streams = await api.listStreams();
    const first = streams[0];
    const found = await api.getStream(first.streamId);
    expect(found?.streamId).toBe(first.streamId);
  });

  it("returns undefined for an unknown stream", async () => {
    const found = await api.getStream("does-not-exist");
    expect(found).toBeUndefined();
  });

  it("returns only a streamer's streams", async () => {
    const streams = await api.getStreamerStreams("alice");
    expect(streams.length).toBeGreaterThan(0);
    expect(streams.every((s) => s.publisher === "alice")).toBe(true);
  });

  it("returns stats for a live stream", async () => {
    const streams = await api.listStreams();
    const live = streams.find((s) => s.status === "live");
    expect(live).toBeDefined();
    const stats = await api.getStreamStats(live!.streamId);
    expect(stats.viewers).toBeGreaterThan(0);
    expect(stats.bufferState).toBe("healthy");
  });

  it("subscribes to live stats", async () => {
    const streams = await api.listStreams();
    const live = streams.find((s) => s.status === "live");
    expect(live).toBeDefined();
    let received: StreamStats | undefined;
    const unsubscribe = api.subscribeStats(live!.streamId, (s) => {
      received = s;
    });
    expect(received).toBeDefined();
    expect(received!.viewers).toBeGreaterThan(0);
    unsubscribe();
  });
});
