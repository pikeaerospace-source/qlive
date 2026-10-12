/**
 * Tests for the streamer profile page.
 *
 * The data service is mocked at the API boundary (`../data/api`), so these run
 * offline and assert loading, error, not-found, and happy-path rendering.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Stream, Streamer } from "../types";
import ProfilePage from "./ProfilePage";

const mocks = vi.hoisted(() => ({
  getStreamer: vi.fn(),
  getStreamerStreams: vi.fn(),
}));

vi.mock("../data/api", () => ({
  selectApi: () => ({
    getStreamer: mocks.getStreamer,
    getStreamerStreams: mocks.getStreamerStreams,
  }),
}));

const streamer: Streamer = {
  name: "alice",
  bio: "Building things on Qortal.",
  followers: 1234,
  verified: true,
};

const stream: Stream = {
  streamId: "s1",
  publisher: "alice",
  title: "Live stream",
  description: "",
  category: "gaming",
  startedAt: 1_000,
  status: "live",
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 30 },
  bitrate: { video: 4_500_000, audio: 128_000 },
  viewers: 12,
};

function renderAt(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/profile/${name}`]}>
      <Routes>
        <Route path="/profile/:name" element={<ProfilePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    mocks.getStreamer.mockReset();
    mocks.getStreamerStreams.mockReset();
    mocks.getStreamer.mockResolvedValue(streamer);
    mocks.getStreamerStreams.mockResolvedValue([stream]);
  });

  it("renders the streamer's profile and streams", async () => {
    renderAt("alice");

    expect(
      await screen.findByRole("heading", { name: /alice/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Building things on Qortal.")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(await screen.findByText("Live stream")).toBeInTheDocument();
  });

  it("shows an empty state when the streamer has no streams", async () => {
    mocks.getStreamerStreams.mockResolvedValue([]);
    renderAt("alice");

    expect(await screen.findByText("No streams yet.")).toBeInTheDocument();
  });

  it("shows a skeleton while loading", () => {
    mocks.getStreamer.mockReturnValue(new Promise(() => {})); // never resolves
    renderAt("alice");

    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });

  it("shows an error notice with retry when the fetch fails", async () => {
    mocks.getStreamer.mockRejectedValue(new Error("node offline"));
    renderAt("alice");

    expect(
      await screen.findByText("Couldn’t load this profile"),
    ).toBeInTheDocument();
    expect(screen.getByText("node offline")).toBeInTheDocument();

    mocks.getStreamer.mockResolvedValue(streamer);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(
      await screen.findByRole("heading", { name: /alice/ }),
    ).toBeInTheDocument();
  });

  it("reports a missing streamer", async () => {
    mocks.getStreamer.mockResolvedValue(undefined);
    renderAt("nobody");

    expect(await screen.findByText("Streamer not found.")).toBeInTheDocument();
  });
});
