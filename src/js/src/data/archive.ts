/**
 * QLive — live → VOD replay state.
 *
 * Derives the viewer-facing replay state of a stream from its archive metadata
 * (docs/vod-pipeline.md) and formats archive metrics for display.
 *
 * The archive reuses the original live fragments verbatim — no re-encoding — so
 * "watch replay" is only a matter of publishing (or pointing at) the archived
 * QDN resource. An ended stream therefore moves through `archiving` (VOD engine
 * finalising) to `ready` (or `partial` when the stream was interrupted) without
 * any transcoding step.
 */

import type { Stream } from "../types";

/** Viewer-facing replay availability. */
export type ReplayState = "none" | "archiving" | "ready" | "partial";

/**
 * Replay state of a stream.
 *
 * - `ready` / `partial` — archive metadata is present and published.
 * - `archiving` — the stream finished but the archive is not published yet.
 * - `none` — nothing to replay (live, upcoming, or an unknown archive state).
 */
export function replayState(stream: Stream): ReplayState {
  if (stream.archive) {
    if (stream.archive.status === "archived") return "ready";
    if (stream.archive.status === "partial") return "partial";
    return "archiving";
  }
  // No archive block yet: a finished stream is still being archived, while a
  // stream already marked `archived` without metadata is assumed replayable.
  if (stream.status === "ended" || stream.status === "interrupted") {
    return "archiving";
  }
  if (stream.status === "archived") return "ready";
  return "none";
}

/** True when a published replay exists (complete or partial). */
export function hasReplay(stream: Stream): boolean {
  const state = replayState(stream);
  return state === "ready" || state === "partial";
}

/** Action label for a replay state (empty for `none`). */
export function replayLabel(state: ReplayState): string {
  switch (state) {
    case "ready":
      return "Watch replay";
    case "partial":
      return "Watch partial replay";
    case "archiving":
      return "Archiving…";
    case "none":
      return "";
  }
}

/**
 * Sort key for "recently ended" listings: archive publish time when known,
 * otherwise when the stream started.
 */
export function replaySortKey(stream: Stream): number {
  return stream.archive?.publishedAt ?? stream.startedAt;
}

/** Human-readable duration, e.g. `45s`, `3m 12s`, `1h 4m`. */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  return `${seconds}s`;
}

/** Human-readable byte size, e.g. `512 B`, `4.5 MB`, `1.2 GB`. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}
