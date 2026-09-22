/**
 * Tests for the watch page's live → VOD replay transition.
 *
 * The data service is mocked at the API boundary (`../data/api`), so these run
 * offline and assert only the page's rendering/behaviour.
 */

import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Stream } from "../types";
import WatchPage from "./WatchPage";

const mocks = vi.hoisted(() => ({
  getStream: vi.fn(),
  subscribeStats: vi.fn(() => () => {}),
}));

vi.mock("../data/api", () => ({
  selectApi: () => ({
    getStream: mocks.getStream,
    subscribeStats: mocks.subscribeStats,
  }),
}));

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
  viewers: 42,
  ...overrides,
});

const archivedStream = stream({
  streamId: "arch1",
  status: "archived",
  viewers: 0,
  playbackUrl: "/arbitrary/VIDEO/alice/qlive-archive-arch1",
  archive: {
    qdnResourceId: "qlive-archive-arch1",
    qtubeManifestId: "qlive-manifest-arch1",
    status: "archived",
    publishedAt: 2_000,
    durationMs: 2_520_000,
    sizeBytes: 828_000_000,
    fragmentCount: 2_520,
  },
});

function renderAt(streamId: string) {
  return render(
    <MemoryRouter initialEntries={[`/watch/${streamId}`]}>
      <Routes>
        <Route path="/watch/:streamId" element={<WatchPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("WatchPage", () => {
  beforeEach(() => {
    mocks.getStream.mockReset();
    mocks.subscribeStats.mockClear();
  });

  it("plays the archive and links the replay for an archived stream", async () => {
    mocks.getStream.mockResolvedValue(archivedStream);
    renderAt("arch1");

    expect(await screen.findByText("Replay available")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Watch replay" }),
    ).toHaveAttribute(
      "href",
      "/arbitrary/VIDEO/alice/qlive-archive-arch1",
    );
    expect(screen.getByText(/no re-encoding/)).toBeInTheDocument();
    expect(screen.getByText("Duration 42m")).toBeInTheDocument();
    expect(screen.getByText("Size 789.6 MB")).toBeInTheDocument();
    expect(screen.getByText("2,520 fragments")).toBeInTheDocument();
    // Finished streams have no live stats socket.
    expect(mocks.subscribeStats).not.toHaveBeenCalled();
  });

  it("warns that an interrupted archive is partial", async () => {
    mocks.getStream.mockResolvedValue(
      stream({
        streamId: "part1",
        status: "interrupted",
        viewers: 0,
        archive: {
          qdnResourceId: "qlive-archive-part1",
          status: "partial",
          durationMs: 1_380_000,
          sizeBytes: 809_000_000,
          fragmentCount: 1_380,
        },
      }),
    );
    renderAt("part1");

    expect(await screen.findByText("Partial replay")).toBeInTheDocument();
    expect(screen.getByText(/replay is incomplete/)).toBeInTheDocument();
    expect(
      screen.getByText(/Replay source unavailable in mock\/offline mode/),
    ).toBeInTheDocument();
  });

  it("shows an archiving notice for an ended stream without an archive", async () => {
    mocks.getStream.mockResolvedValue(
      stream({ streamId: "end1", status: "ended", viewers: 0 }),
    );
    renderAt("end1");

    expect(await screen.findByText("Archiving…")).toBeInTheDocument();
    expect(
      screen.getByText(/published to QDN/),
    ).toBeInTheDocument();
    expect(screen.queryByText("Replay available")).not.toBeInTheDocument();
  });

  it("subscribes to live stats and shows the live stat row for a live stream", async () => {
    mocks.getStream.mockResolvedValue(stream({ streamId: "live1" }));
    renderAt("live1");

    expect(await screen.findByText("Viewers")).toBeInTheDocument();
    expect(screen.queryByText("Replay available")).not.toBeInTheDocument();
    expect(mocks.subscribeStats).toHaveBeenCalledWith(
      "live1",
      expect.any(Function),
    );
  });

  it("reports a missing stream", async () => {
    mocks.getStream.mockResolvedValue(undefined);
    renderAt("nope");

    expect(await screen.findByText("Stream not found.")).toBeInTheDocument();
  });
});
