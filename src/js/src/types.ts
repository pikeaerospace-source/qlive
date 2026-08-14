export type StreamStatus =
  | "announced"
  | "live"
  | "ended"
  | "archived"
  | "interrupted";

export interface Resolution {
  width: number;
  height: number;
  fps: number;
}

export interface Bitrate {
  /** Video bitrate in bits per second. */
  video: number;
  /** Audio bitrate in bits per second. */
  audio: number;
}

export interface Stream {
  streamId: string;
  /** The broadcaster's Qortal Name. */
  publisher: string;
  title: string;
  description: string;
  category: string;
  /** Unix epoch milliseconds. */
  startedAt: number;
  status: StreamStatus;
  fragmentDurationMs: number;
  resolution: Resolution;
  bitrate: Bitrate;
  /** Current concurrent viewers (derived from swarm). */
  viewers: number;
  thumbnail?: string;
  /** Optional HLS/CMAF playback URL. Absent in offline/mock mode. */
  playbackUrl?: string;
}

export interface Streamer {
  /** The streamer's Qortal Name. */
  name: string;
  bio: string;
  followers: number;
  verified: boolean;
}

export type BufferState = "filling" | "healthy" | "stalling" | "overflow";

export interface StreamStats {
  viewers: number;
  bandwidthKbps: number;
  bufferState: BufferState;
  chunksProduced: number;
  retransmissions: number;
}
