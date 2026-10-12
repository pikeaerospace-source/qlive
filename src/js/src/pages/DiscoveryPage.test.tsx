/**
 * Tests for the stream discovery page.
 *
 * The data service is mocked at the API boundary (`../data/api`), so these run
 * offline and assert the live grid plus the "Recently ended" replay section.
 */

import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearFollows, toggleFollow } from "../data/follows";
import type { Stream } from "../types";
import DiscoveryPage from "./DiscoveryPage";

const mocks = vi.hoisted(() => ({ listStreams: vi.fn() }));

vi.mock("../data/api", () => ({
  selectApi: () => ({ listStreams: mocks.listStreams }),
}));

const stream = (overrides: Partial<Stream> = {}): Stream => ({
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
  ...overrides,
});

const replayable = stream({
  streamId: "arch1",
  title: "Archived talk",
  status: "archived",
  viewers: 0,
  archive: {
    qdnResourceId: "qlive-archive-arch1",
    status: "archived",
    publishedAt: 5_000,
    durationMs: 2_520_000,
    sizeBytes: 828_000_000,
    fragmentCount: 2_520,
  },
});

const archiving = stream({
  streamId: "end1",
  title: "Just ended",
  status: "ended",
  viewers: 0,
});

const featured = stream({
  streamId: "feat1",
  title: "Featured stream",
  publisher: "carol",
  viewers: 900,
  featured: true,
});

function renderPage() {
  return render(
    <MemoryRouter>
      <DiscoveryPage />
    </MemoryRouter>,
  );
}

describe("DiscoveryPage", () => {
  beforeEach(() => {
    clearFollows();
    mocks.listStreams.mockReset();
    mocks.listStreams.mockResolvedValue([stream(), replayable, archiving]);
  });

  it("lists live streams in the main grid", async () => {
    renderPage();
    // The live stream also shows in the Trending row, so it appears at least once.
    expect((await screen.findAllByText("Live stream")).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getByRole("heading", { name: "Live & upcoming" }),
    ).toBeInTheDocument();

    const recentHeading = screen.getByRole("heading", {
      name: "Recently ended",
    });
    expect(recentHeading).toBeInTheDocument();
    // Archive-worthy streams move out of the live grid into the replay section.
    expect(screen.getAllByText("Archived talk")).toHaveLength(1);
  });

  it("links to the replay of an archived stream only", async () => {
    renderPage();
    const links = await screen.findAllByRole("link", { name: /Watch replay/ });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/watch/arch1");
    expect(screen.getByText("42m")).toBeInTheDocument();
  });

  it("marks a finished stream that is still being archived", async () => {
    renderPage();
    expect(await screen.findByText(/Replay archiving/)).toBeInTheDocument();
    expect(screen.getByText("Just ended")).toBeInTheDocument();
  });

  it("filters both sections by the search query", async () => {
    renderPage();
    expect((await screen.findAllByText("Live stream")).length).toBeGreaterThan(
      0,
    );

    fireEvent.change(screen.getByLabelText("Search streams"), {
      target: { value: "archived talk" },
    });

    expect(screen.getByText("Archived talk")).toBeInTheDocument();
    expect(screen.queryAllByText("Live stream")).toHaveLength(0);
    expect(screen.queryByText("Just ended")).not.toBeInTheDocument();
  });

  it("shows a Featured row for curated streams", async () => {
    mocks.listStreams.mockResolvedValue([stream(), featured]);
    renderPage();

    await screen.findAllByText("Featured stream");
    const section = screen.getByRole("heading", { name: "Featured" })
      .parentElement as HTMLElement;
    expect(within(section).getByText("Featured stream")).toBeInTheDocument();
  });

  it("shows a Trending row excluding featured streams", async () => {
    mocks.listStreams.mockResolvedValue([stream(), featured]);
    renderPage();

    await screen.findByRole("heading", { name: "Trending now" });
    const trending = screen.getByRole("heading", { name: "Trending now" })
      .parentElement as HTMLElement;
    expect(within(trending).getByText("Live stream")).toBeInTheDocument();
    // The featured stream is highlighted separately, not in Trending.
    expect(
      within(trending).queryByText("Featured stream"),
    ).not.toBeInTheDocument();
  });

  it("shows a Following row once the viewer follows a streamer", async () => {
    toggleFollow("alice");
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Following" }),
    ).toBeInTheDocument();
  });

  it("omits the Following row when nothing is followed", async () => {
    renderPage();
    await screen.findAllByText("Live stream");

    expect(
      screen.queryByRole("heading", { name: "Following" }),
    ).not.toBeInTheDocument();
  });

  it("shows a loading skeleton while fetching", () => {
    mocks.listStreams.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();

    expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    expect(
      screen.queryByText("No streams match your search."),
    ).not.toBeInTheDocument();
  });

  it("shows an error notice with retry when the fetch fails", async () => {
    mocks.listStreams.mockRejectedValue(new Error("QDN unreachable"));
    renderPage();

    expect(
      await screen.findByText("Couldn’t load streams"),
    ).toBeInTheDocument();
    expect(screen.getByText("QDN unreachable")).toBeInTheDocument();

    mocks.listStreams.mockResolvedValue([stream()]);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect((await screen.findAllByText("Live stream")).length).toBeGreaterThan(
      0,
    );
  });
});
