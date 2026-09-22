/**
 * Tests for the stream player's playback states and error recovery.
 *
 * `hls.js` is mocked (including its dynamic import), so the recovery paths run
 * offline and deterministically.
 */

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Stream } from "../types";
import Player, { RETRY_BACKOFF_MS } from "./Player";

type Handler = (event: string, data: unknown) => void;
type FatalData = { fatal: boolean; type: string };

const { FakeHls } = vi.hoisted(() => {
  class FakeHls {
    static instances: FakeHls[] = [];
    static supported = true;
    static Events = { ERROR: "hlsError" };
    static ErrorTypes = {
      NETWORK_ERROR: "networkError",
      MEDIA_ERROR: "mediaError",
      OTHER_ERROR: "otherError",
    };

    handlers: Record<string, Handler> = {};
    config: { lowLatencyMode?: boolean } = {};
    loadedSources: string[] = [];
    startLoadCalls = 0;
    recoverMediaErrorCalls = 0;
    destroyed = false;

    constructor(config?: { lowLatencyMode?: boolean }) {
      this.config = config ?? {};
      FakeHls.instances.push(this);
    }

    static isSupported() {
      return FakeHls.supported;
    }

    static reset() {
      FakeHls.instances = [];
      FakeHls.supported = true;
    }

    on(event: string, cb: Handler) {
      this.handlers[event] = cb;
    }

    /** Fire a recorded hls.js event (as hls.js would). */
    emit(event: string, data: unknown) {
      this.handlers[event]?.(event, data);
    }

    loadSource(url: string) {
      this.loadedSources.push(url);
    }

    attachMedia() {
      /* no-op */
    }

    startLoad() {
      this.startLoadCalls += 1;
    }

    recoverMediaError() {
      this.recoverMediaErrorCalls += 1;
    }

    destroy() {
      this.destroyed = true;
    }
  }

  return { FakeHls };
});

vi.mock("hls.js", () => ({ default: FakeHls }));

const stream = (overrides: Partial<Stream> = {}): Stream => ({
  streamId: "s1",
  publisher: "alice",
  title: "Test stream",
  description: "",
  category: "gaming",
  startedAt: 1,
  status: "live",
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 30 },
  bitrate: { video: 4_500_000, audio: 128_000 },
  viewers: 0,
  playbackUrl: "/live/s1.m3u8",
  ...overrides,
});

type FakeHlsInstance = InstanceType<typeof FakeHls>;

/** Render a player and let the dynamic `import("hls.js")` resolve. */
async function renderPlayer(
  overrides: Partial<Stream> = {},
): Promise<FakeHlsInstance> {
  render(<Player stream={stream(overrides)} />);
  for (let i = 0; i < 5; i += 1) await act(async () => {});
  return FakeHls.instances[FakeHls.instances.length - 1];
}

const overlay = () => screen.queryByRole("status");
const video = () => document.querySelector("video") as HTMLVideoElement;

/** Emit a fatal hls.js error. */
const emitError = (hls: FakeHlsInstance, data: FatalData) =>
  act(() => hls.emit("hlsError", data));

const markPlaying = () =>
  act(() => {
    video().dispatchEvent(new Event("playing"));
  });

const advanceBackoff = () =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_MS + 1);
  });

describe("Player", () => {
  beforeEach(() => {
    FakeHls.reset();
    vi.useRealTimers();
  });

  it("shows an offline placeholder when there is no playback URL", () => {
    render(<Player stream={stream({ playbackUrl: undefined })} />);

    expect(screen.getByText(/No live source available/)).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("attaches hls.js in low-latency mode for a live stream", async () => {
    const hls = await renderPlayer();

    expect(hls.loadedSources).toEqual(["/live/s1.m3u8"]);
    expect(hls.config.lowLatencyMode).toBe(true);
    expect(overlay()).toHaveAttribute("data-playback-state", "connecting");

    markPlaying();
    expect(overlay()).not.toBeInTheDocument();
  });

  it("plays archives at normal latency", async () => {
    const hls = await renderPlayer({ status: "archived" });
    expect(hls.config.lowLatencyMode).toBe(false);
  });

  it("reports a browser that cannot play the stream", async () => {
    FakeHls.supported = false;
    await renderPlayer();

    expect(overlay()).toHaveAttribute("data-playback-state", "unsupported");
    expect(screen.getByText(/cannot play the stream/)).toBeInTheDocument();
  });

  it("auto-recovers a fatal network error after a backoff", async () => {
    vi.useFakeTimers();
    const hls = await renderPlayer();

    emitError(hls, { fatal: true, type: "networkError" });
    expect(overlay()).toHaveAttribute("data-playback-state", "recovering");
    expect(hls.startLoadCalls).toBe(0);

    await advanceBackoff();
    expect(hls.startLoadCalls).toBe(1);

    markPlaying();
    expect(overlay()).not.toBeInTheDocument();
  });

  it("ignores non-fatal errors", async () => {
    const hls = await renderPlayer();

    emitError(hls, { fatal: false, type: "networkError" });

    expect(overlay()).toHaveAttribute("data-playback-state", "connecting");
    expect(hls.startLoadCalls).toBe(0);
  });

  it("recovers a fatal media error once, then interrupts", async () => {
    const hls = await renderPlayer();

    emitError(hls, { fatal: true, type: "mediaError" });
    expect(hls.recoverMediaErrorCalls).toBe(1);
    expect(overlay()).toHaveAttribute("data-playback-state", "recovering");

    emitError(hls, { fatal: true, type: "mediaError" });
    expect(overlay()).toHaveAttribute("data-playback-state", "interrupted");
  });

  it("interrupts on a fatal error it cannot recover", async () => {
    const hls = await renderPlayer();

    emitError(hls, { fatal: true, type: "otherError" });

    expect(overlay()).toHaveAttribute("data-playback-state", "interrupted");
  });

  it("asks the viewer to retry once auto-recovery is exhausted", async () => {
    vi.useFakeTimers();
    const hls = await renderPlayer();

    for (let i = 0; i < 3; i += 1) {
      emitError(hls, { fatal: true, type: "networkError" });
      await advanceBackoff();
    }

    expect(hls.startLoadCalls).toBe(2); // two automatic attempts, then stop
    expect(overlay()).toHaveAttribute("data-playback-state", "interrupted");
    expect(screen.getByText("Playback interrupted")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    for (let i = 0; i < 5; i += 1) await act(async () => {});

    expect(FakeHls.instances).toHaveLength(2);
    expect(FakeHls.instances[0].destroyed).toBe(true);
    expect(overlay()).toHaveAttribute("data-playback-state", "connecting");
  });
});
