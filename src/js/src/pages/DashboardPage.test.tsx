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
import DashboardPage, { ARCHIVE_POLL_MS } from "./DashboardPage";

const mocks = vi.hoisted(() => ({
  publishStream: vi.fn(),
  unpublishStream: vi.fn(),
  getStream: vi.fn(),
}));

vi.mock("../data/publisher", () => ({
  selectPublisher: () => ({
    publishStream: mocks.publishStream,
    unpublishStream: mocks.unpublishStream,
  }),
}));

vi.mock("../data/api", () => ({
  selectApi: () => ({ getStream: mocks.getStream }),
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
