export type StreamStatus =
  | "announced"
  | "live"
  | "ended"
  | "archived"
  | "interrupted";

/** Archive lifecycle of a completed stream (see docs/vod-pipeline.md). */
export type ArchiveStatus = "pending" | "archived" | "partial";

/**
 * Q-Tube/QDN archive metadata for a completed live stream.
 *
 * Mirrors the `archive` block of the `qlive-stream` QDN document and the
 * `QTubeManifest` produced by `qlive/archival.py`. The archived video reuses
 * the original live fragments — no re-encoding — so a replay only needs the
 * QDN resource id plus the viewer-facing metrics below.
 */
export interface StreamArchive {
  /** QDN identifier of the archived video resource (`Service.VIDEO`). */
  qdnResourceId: string;
  /** QDN identifier of the Q-Tube manifest document (`Service.JSON`). */
  qtubeManifestId?: string;
  /** Published archive state; `partial` = stream interrupted mid-way. */
  status: ArchiveStatus;
  /** Unix epoch ms when the archive was published to QDN. */
  publishedAt?: number;
  /** Archived duration in milliseconds. */
  durationMs?: number;
  /** Total archived size in bytes. */
  sizeBytes?: number;
  /** Number of archived fragments (live chunks). */
  fragmentCount?: number;
}

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
  /** Archive metadata once the VOD engine has committed the stream. */
  archive?: StreamArchive;
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
