/**
 * Tests for the broadcaster dashboard's QDN signaling wiring.
 *
 * The publisher seam (`../data/publisher`) is mocked, so these run offline and
 * assert the metadata published on start/stop plus the signaling panel.
 */

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Stream, StreamStatus } from "../types";
import DashboardPage, {
  ARCHIVE_POLL_MS,
  BANDWIDTH_SAMPLES,
} from "./DashboardPage";

const mocks = vi.hoisted(() => ({
  publishStream: vi.fn(),
  unpublishStream: vi.fn(),
  getStream: vi.fn(),
  subscribeStats: vi.fn(),
}));

vi.mock("../data/publisher", () => ({
  selectPublisher: () => ({
    publishStream: mocks.publishStream,
    unpublishStream: mocks.unpublishStream,
  }),
}));

vi.mock("../data/api", () => ({
  selectApi: () => ({
    getStream: mocks.getStream,
    subscribeStats: mocks.subscribeStats,
  }),
}));

/** Minimal stream shape for the archive read-back poll. */
const archivedStream = (streamId: string): Partial<Stream> => ({
  streamId,
  status: "archived",
});

/**
 * Flush pending microtasks inside `act`. Use instead of `waitFor`/`findBy*`,
 * which can't drive vitest's fake timers (no global `jest` to detect them).
 */
async function flush(rounds = 6) {
  for (let i = 0; i < rounds; i += 1) await act(async () => {});
}

/** Minimal publish result mirroring what the adapter returns. */
const publishedResult = (streamId: string, status: StreamStatus) => ({
  name: "alice",
  identifier: `QLIVE_STREAM_${streamId}`,
  service: "JSON",
  doc: {
    type: "qlive-stream",
    version: 1,
    publisher: "alice",
    title: "My Live Stream",
    category: "gaming",
    startedAt: 1,
    status,
    fragmentDurationMs: 1000,
    resolution: { width: 1920, height: 1080, fps: 30 },
    bitrate: { video: 4_500_000, audio: 128_000 },
  },
});

describe("DashboardPage signaling", () => {
  beforeEach(() => {
    vi.useRealTimers();
    mocks.publishStream.mockReset();
    mocks.publishStream.mockImplementation(
      (pub: { streamId: string; status: StreamStatus }) =>
        Promise.resolve(publishedResult(pub.streamId, pub.status)),
    );
    mocks.getStream.mockReset();
    mocks.getStream.mockResolvedValue(undefined);
    mocks.subscribeStats.mockReset();
    mocks.subscribeStats.mockReturnValue(() => {});
  });

  it("publishes a live stream doc when the broadcast starts", async () => {
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));

    await waitFor(() => expect(mocks.publishStream).toHaveBeenCalledTimes(1));
    const pub = mocks.publishStream.mock.calls[0][0];
    expect(pub.status).toBe("live");
    expect(pub.title).toBe("My Live Stream");
    expect(pub.category).toBe("gaming");
    expect(pub.streamId).toMatch(/^[0-9a-f]{12}$/);
    expect(pub.startedAt).toBeGreaterThan(0);

    expect(await screen.findByText("Metadata published")).toBeInTheDocument();
    expect(
      screen.getByText(`QLIVE_STREAM_${pub.streamId}`),
    ).toBeInTheDocument();
    expect(screen.getByText("publisher: alice")).toBeInTheDocument();
  });

  it("re-publishes the same identifier as ended when the broadcast stops", async () => {
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");

    fireEvent.click(screen.getByRole("button", { name: "Stop broadcast" }));

    await waitFor(() => expect(mocks.publishStream).toHaveBeenCalledTimes(2));
    const [first, second] = mocks.publishStream.mock.calls;
    expect(second[0].streamId).toBe(first[0].streamId);
    expect(second[0].status).toBe("ended");
    expect(second[0].startedAt).toBe(first[0].startedAt);
  });

  it("shows an archiving indicator once the broadcast stops", async () => {
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");
    expect(screen.queryByText("Archiving…")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Stop broadcast" }));

    expect(await screen.findByText("Archiving…")).toBeInTheDocument();
  });

  it("clears the archiving indicator once the archive completes", async () => {
    vi.useFakeTimers();
    try {
      render(<DashboardPage />);
      fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
      await flush();
      expect(screen.getByText("Metadata published")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Stop broadcast" }));
      await flush();
      expect(screen.getByText("Archiving…")).toBeInTheDocument();

      // The VOD engine finishes; the next read-back reports `archived`.
      const streamId = mocks.publishStream.mock.calls[1][0].streamId;
      mocks.getStream.mockResolvedValue(archivedStream(streamId));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(ARCHIVE_POLL_MS + 1);
      });
      await flush();

      expect(
        screen.getByText(/Replay archive published to QDN/),
      ).toBeInTheDocument();
      expect(screen.getAllByText("Archived").length).toBeGreaterThan(0);
      expect(screen.queryByText("Archiving…")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("starts a new stream id for the next broadcast", async () => {
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");
    fireEvent.click(screen.getByRole("button", { name: "Stop broadcast" }));
    await waitFor(() => expect(mocks.publishStream).toHaveBeenCalledTimes(2));

    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await waitFor(() => expect(mocks.publishStream).toHaveBeenCalledTimes(3));
    expect(mocks.publishStream.mock.calls[2][0].streamId).not.toBe(
      mocks.publishStream.mock.calls[0][0].streamId,
    );
  });

  it("surfaces a publish failure", async () => {
    mocks.publishStream.mockRejectedValue(new Error("no Qortal Name"));
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));

    expect(await screen.findByText("Publish failed")).toBeInTheDocument();
    expect(screen.getByText("no Qortal Name")).toBeInTheDocument();
  });

  it("shows an empty state before the first broadcast", () => {
    render(<DashboardPage />);

    expect(
      screen.getByText(
        "No broadcast yet — start one to see stream health here.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Viewers")).not.toBeInTheDocument();
  });
});

describe("DashboardPage live stats", () => {
  beforeEach(() => {
    mocks.publishStream.mockReset();
    mocks.publishStream.mockImplementation(
      (pub: { streamId: string; status: StreamStatus }) =>
        Promise.resolve(publishedResult(pub.streamId, pub.status)),
    );
    mocks.getStream.mockReset();
    mocks.getStream.mockResolvedValue(undefined);
    mocks.subscribeStats.mockReset();
    mocks.subscribeStats.mockReturnValue(() => {});
  });

  /** Read a stat widget's value by its label. */
  const statValue = (label: string) =>
    screen.getByText(label).parentElement?.querySelector(".stat__value")
      ?.textContent;

  const emit = (stats: {
    viewers?: number;
    bandwidthKbps?: number;
    bufferState?: string;
    chunksProduced?: number;
    retransmissions?: number;
  }) => {
    mocks.subscribeStats.mockImplementation(
      (_id: string, cb: (s: unknown) => void) => {
        cb({
          viewers: 0,
          bandwidthKbps: 0,
          bufferState: "healthy",
          chunksProduced: 0,
          retransmissions: 0,
          ...stats,
        });
        return () => {};
      },
    );
  };

  it("does not subscribe to stats before broadcasting", () => {
    render(<DashboardPage />);
    expect(mocks.subscribeStats).not.toHaveBeenCalled();
  });

  it("renders the live health widgets from the stats feed", async () => {
    emit({
      viewers: 42,
      bandwidthKbps: 4500,
      bufferState: "healthy",
      chunksProduced: 120,
      retransmissions: 3,
    });
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");

    expect(await screen.findByText("4.5 Mbps")).toBeInTheDocument();
    expect(statValue("Viewers")).toBe("42");
    expect(statValue("Buffer")).toBe("healthy");
    expect(statValue("Chunks")).toBe("120");
    expect(statValue("Retransmissions")).toBe("3");
    expect(
      screen.getByRole("img", { name: "Bandwidth over time (kbps)" }),
    ).toBeInTheDocument();
  });

  it("tones the buffer stat by buffer health", async () => {
    emit({ bufferState: "stalling" });
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");

    expect(await screen.findByText("stalling")).toHaveClass(
      "stat__value--danger",
    );
  });

  it("caps the bandwidth history window", async () => {
    mocks.subscribeStats.mockImplementation(
      (_id: string, cb: (s: unknown) => void) => {
        for (let i = 0; i < 60; i += 1) {
          cb({
            viewers: 1,
            bandwidthKbps: 1000 + i,
            bufferState: "healthy",
            chunksProduced: i,
            retransmissions: 0,
          });
        }
        return () => {};
      },
    );
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");

    expect(
      await screen.findByText(`${BANDWIDTH_SAMPLES} samples`),
    ).toBeInTheDocument();
  });

  it("unsubscribes from stats when the broadcast stops", async () => {
    const unsubscribe = vi.fn();
    mocks.subscribeStats.mockReturnValue(unsubscribe);
    render(<DashboardPage />);
    fireEvent.click(screen.getByRole("button", { name: "Start broadcast" }));
    await screen.findByText("Metadata published");

    fireEvent.click(screen.getByRole("button", { name: "Stop broadcast" }));

    await waitFor(() => expect(unsubscribe).toHaveBeenCalled());
  });
});
