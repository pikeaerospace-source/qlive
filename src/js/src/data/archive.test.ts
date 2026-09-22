/**
 * Tests for the live → VOD replay state helpers.
 */

import { describe, expect, it } from "vitest";

import type { Stream, StreamArchive } from "../types";
import {
  formatBytes,
  formatDuration,
  hasReplay,
  replayLabel,
  replaySortKey,
  replayState,
} from "./archive";

const archive = (overrides: Partial<StreamArchive> = {}): StreamArchive => ({
  qdnResourceId: "qlive-archive-1",
  status: "archived",
  ...overrides,
});

const stream = (overrides: Partial<Stream> = {}): Stream => ({
  streamId: "s1",
  publisher: "alice",
  title: "Test stream",
  description: "",
  category: "gaming",
  startedAt: 1_000,
  status: "live",
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 30 },
  bitrate: { video: 4_500_000, audio: 128_000 },
  viewers: 0,
  ...overrides,
});

describe("replayState", () => {
  it("reports no replay for live and upcoming streams", () => {
    expect(replayState(stream({ status: "live" }))).toBe("none");
    expect(replayState(stream({ status: "announced" }))).toBe("none");
  });

  it("reports archiving for a finished stream with no archive metadata", () => {
    expect(replayState(stream({ status: "ended" }))).toBe("archiving");
    expect(replayState(stream({ status: "interrupted" }))).toBe("archiving");
  });

  it("maps published archive metadata to ready/partial", () => {
    expect(replayState(stream({ status: "archived", archive: archive() }))).toBe(
      "ready",
    );
    expect(
      replayState(
        stream({
          status: "interrupted",
          archive: archive({ status: "partial" }),
        }),
      ),
    ).toBe("partial");
  });

  it("treats a pending archive as still archiving", () => {
    expect(
      replayState(stream({ status: "ended", archive: archive({ status: "pending" }) })),
    ).toBe("archiving");
  });

  it("assumes a replay for an archived stream with no metadata", () => {
    expect(replayState(stream({ status: "archived" }))).toBe("ready");
  });
});

describe("hasReplay", () => {
  it("is true only once the archive is published", () => {
    expect(
      hasReplay(stream({ status: "archived", archive: archive() })),
    ).toBe(true);
    expect(
      hasReplay(
        stream({ status: "interrupted", archive: archive({ status: "partial" }) }),
      ),
    ).toBe(true);
    expect(hasReplay(stream({ status: "ended" }))).toBe(false);
    expect(hasReplay(stream({ status: "live" }))).toBe(false);
  });
});

describe("replayLabel", () => {
  it("labels each replay state", () => {
    expect(replayLabel("ready")).toBe("Watch replay");
    expect(replayLabel("partial")).toBe("Watch partial replay");
    expect(replayLabel("archiving")).toBe("Archiving…");
    expect(replayLabel("none")).toBe("");
  });
});

describe("replaySortKey", () => {
  it("prefers the archive publish time", () => {
    expect(
      replaySortKey(stream({ startedAt: 5, archive: archive({ publishedAt: 9 }) })),
    ).toBe(9);
  });

  it("falls back to the stream start time", () => {
    expect(replaySortKey(stream({ startedAt: 5 }))).toBe(5);
  });
});

describe("formatDuration", () => {
  it("formats seconds, minutes and hours", () => {
    expect(formatDuration(45_000)).toBe("45s");
    expect(formatDuration(90_000)).toBe("1m 30s");
    expect(formatDuration(2_520_000)).toBe("42m");
    expect(formatDuration(3_720_000)).toBe("1h 2m");
  });

  it("clamps negative durations", () => {
    expect(formatDuration(-1)).toBe("0s");
  });
});

describe("formatBytes", () => {
  it("formats bytes, KB, MB and GB", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5_242_880)).toBe("5.0 MB");
    expect(formatBytes(828_000_000)).toBe("789.6 MB");
    expect(formatBytes(1_073_741_824)).toBe("1.0 GB");
  });
});
