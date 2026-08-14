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
});
