import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Stream } from "../types";
import StreamCard from "./StreamCard";

const stream: Stream = {
  streamId: "test-1",
  publisher: "alice",
  title: "Test stream",
  description: "",
  category: "gaming",
  startedAt: Date.now(),
  status: "live",
  fragmentDurationMs: 1000,
  resolution: { width: 1920, height: 1080, fps: 30 },
  bitrate: { video: 4_500_000, audio: 128_000 },
  viewers: 42,
};

const archived: Stream = {
  ...stream,
  streamId: "archived-1",
  status: "archived",
  viewers: 0,
  archive: {
    qdnResourceId: "qlive-archive-archived-1",
    status: "archived",
    publishedAt: Date.now(),
    durationMs: 2_520_000,
    sizeBytes: 828_000_000,
    fragmentCount: 2_520,
  },
};

const ended: Stream = {
  ...stream,
  streamId: "ended-1",
  status: "ended",
  viewers: 0,
};

describe("StreamCard", () => {
  it("renders title, viewer count and live badge", () => {
    render(
      <MemoryRouter>
        <StreamCard stream={stream} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Test stream")).toBeInTheDocument();
    expect(screen.getByText("42 watching")).toBeInTheDocument();
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("alice")).toBeInTheDocument();
  });

  it("hides viewer count when there are no viewers", () => {
    render(
      <MemoryRouter>
        <StreamCard stream={{ ...stream, viewers: 0, status: "announced" }} />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/watching/)).not.toBeInTheDocument();
    expect(screen.getByText("Upcoming")).toBeInTheDocument();
  });

  it("links to the replay of an archived stream", () => {
    render(
      <MemoryRouter>
        <StreamCard stream={archived} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /Watch replay/ })).toHaveAttribute(
      "href",
      "/watch/archived-1",
    );
    expect(screen.getByText("42m")).toBeInTheDocument();
    expect(screen.getByText("Replay")).toBeInTheDocument();
  });

  it("labels a partial archive", () => {
    const partial: Stream = {
      ...archived,
      streamId: "partial-1",
      status: "interrupted",
      archive: { ...archived.archive!, status: "partial" },
    };
    render(
      <MemoryRouter>
        <StreamCard stream={partial} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Watch partial replay/)).toBeInTheDocument();
    expect(screen.getByText("Interrupted")).toBeInTheDocument();
  });

  it("shows an archiving placeholder for a finished stream", () => {
    render(
      <MemoryRouter>
        <StreamCard stream={ended} />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Replay archiving/)).toBeInTheDocument();
    expect(screen.queryByText(/Watch replay/)).not.toBeInTheDocument();
  });
});
