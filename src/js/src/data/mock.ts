import type { Stream, Streamer } from "../types";

export const mockStreamers: Streamer[] = [
  {
    name: "alice",
    bio: "Indie game dev & speedrunner.",
    followers: 1204,
    verified: true,
  },
  {
    name: "bob",
    bio: "Live coding and decentralized-tech talks.",
    followers: 847,
    verified: false,
  },
  {
    name: "carol",
    bio: "Synthwave music production sessions.",
    followers: 3201,
    verified: true,
  },
];

const now = Date.now();
const minutes = (n: number) => n * 60 * 1000;

export const mockStreams: Stream[] = [
  {
    streamId: "a1b2c3d4e5f6",
    publisher: "alice",
    title: "Speedrunning Hollow Knight — Any%",
    description: "Attempting a new personal best.",
    category: "gaming",
    startedAt: now - minutes(45),
    status: "live",
    fragmentDurationMs: 1000,
    resolution: { width: 1920, height: 1080, fps: 60 },
    bitrate: { video: 6_000_000, audio: 128_000 },
    viewers: 312,
  },
  {
    streamId: "f6e5d4c3b2a1",
    publisher: "bob",
    title: "Building a P2P live-streaming protocol",
    description: "Live coding session on QLive internals.",
    category: "tech",
    startedAt: now - minutes(12),
    status: "live",
    fragmentDurationMs: 1000,
    resolution: { width: 1280, height: 720, fps: 30 },
    bitrate: { video: 2_500_000, audio: 128_000 },
    viewers: 89,
  },
  {
    streamId: "112233445566",
    publisher: "carol",
    title: "Synthwave production — live",
    description: "Composing a new track from scratch.",
    category: "music",
    startedAt: now - minutes(90),
    status: "live",
    fragmentDurationMs: 500,
    resolution: { width: 1920, height: 1080, fps: 30 },
    bitrate: { video: 4_500_000, audio: 192_000 },
    viewers: 540,
  },
  {
    streamId: "998877665544",
    publisher: "alice",
    title: "Celeste B-sides — chill run",
    description: "Casual playthrough, no resets.",
    category: "gaming",
    startedAt: now + minutes(120),
    status: "announced",
    fragmentDurationMs: 1000,
    resolution: { width: 1920, height: 1080, fps: 60 },
    bitrate: { video: 6_000_000, audio: 128_000 },
    viewers: 0,
  },
  {
    streamId: "556677889900",
    publisher: "bob",
    title: "Qortal QDN deep dive",
    description: "How QDN stores and serves data.",
    category: "tech",
    startedAt: now - minutes(60 * 24),
    status: "archived",
    fragmentDurationMs: 1000,
    resolution: { width: 1280, height: 720, fps: 30 },
    bitrate: { video: 2_500_000, audio: 128_000 },
    viewers: 0,
  },
];
