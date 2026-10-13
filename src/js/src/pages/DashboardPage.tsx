import { useEffect, useState } from "react";
import Sparkline from "../components/Sparkline";
import Stat, { type StatTone } from "../components/Stat";
import { selectApi } from "../data/api";
import { selectPublisher } from "../data/publisher";
import type { StreamPublishResult } from "../data/qapp";
import type { BufferState, StreamStats, StreamStatus } from "../types";

/**
 * Provisional stream id for a broadcast session.
 *
 * The Python broadcaster derives the stream id from the serialized metadata
 * document (docs/signaling-schema.md); the dashboard generates a stable id per
 * session so every lifecycle re-publish addresses the same QDN resource.
 */
function newStreamId(): string {
  let id = "";
  while (id.length < 12) id += Math.floor(Math.random() * 16).toString(16);
  return id.slice(0, 12);
}

/** Publication defaults until the encoder/segmenter settings are wired in. */
const RESOLUTION = { width: 1920, height: 1080, fps: 30 };
const BITRATE = { video: 4_500_000, audio: 128_000 };
const FRAGMENT_DURATION_MS = 1000;
/** How often to re-read the stream doc while archiving (exported for tests). */
export const ARCHIVE_POLL_MS = 5000;
/** Rolling window of bandwidth samples shown in the dashboard sparkline. */
export const BANDWIDTH_SAMPLES = 40;

/** Colour tone for each swarm buffer-health state. */
const BUFFER_TONE: Record<BufferState, StatTone> = {
  filling: "warning",
  healthy: "healthy",
  stalling: "danger",
  overflow: "danger",
};

/** Format a bandwidth reading in kbps as Mbps. */
const kbpsToMbps = (kbps: number) => `${(kbps / 1000).toFixed(1)} Mbps`;

/** Result of the last signaling write (QDN, or the offline registry). */
type Signaling =
  | { state: "idle" }
  | { state: "publishing"; identifier: string; status: StreamStatus }
  | { state: "published"; result: StreamPublishResult }
  | { state: "error"; message: string };

export default function DashboardPage() {
  const [live, setLive] = useState(false);
  const [title, setTitle] = useState("My Live Stream");
  const [category, setCategory] = useState("gaming");
  const [streamId, setStreamId] = useState<string>();
  const [startedAt, setStartedAt] = useState<number>();
  const [signaling, setSignaling] = useState<Signaling>({ state: "idle" });
  /** True once the stream doc read-back reports the archive is complete. */
  const [archiveDone, setArchiveDone] = useState(false);
  /** Latest live swarm stats (undefined until the first sample arrives). */
  const [stats, setStats] = useState<StreamStats>();
  /** Rolling bandwidth series for the sparkline. */
  const [bandwidthHistory, setBandwidthHistory] = useState<number[]>([]);

  // Subscribe to live swarm stats while broadcasting; reset when it stops.
  useEffect(() => {
    if (!live || !streamId) return;
    setStats(undefined);
    setBandwidthHistory([]);
    return selectApi().subscribeStats(streamId, (next) => {
      setStats(next);
      setBandwidthHistory((history) =>
        [...history, next.bandwidthKbps].slice(-BANDWIDTH_SAMPLES),
      );
    });
  }, [live, streamId]);

  /** Publish (or re-publish) the stream's signaling document. */
  async function publish(id: string, status: StreamStatus, started: number) {
    setSignaling({ state: "publishing", identifier: id, status });
    try {
      const result = await selectPublisher().publishStream({
        streamId: id,
        title,
        category,
        status,
        fragmentDurationMs: FRAGMENT_DURATION_MS,
        resolution: RESOLUTION,
        bitrate: BITRATE,
        startedAt: started,
      });
      setSignaling({ state: "published", result });
    } catch (error) {
      setSignaling({
        state: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }

  async function startBroadcast() {
    const id = newStreamId();
    const started = Date.now();
    setStreamId(id);
    setStartedAt(started);
    setLive(true);
    setArchiveDone(false);
    // Lifecycle: announced → live. The dashboard goes straight to `live`; the
    // `announced` state is for scheduled streams.
    await publish(id, "live", started);
  }

  async function stopBroadcast() {
    setLive(false);
    if (streamId !== undefined && startedAt !== undefined) {
      // Re-publish the same identifier so the QDN resource is updated in place.
      await publish(streamId, "ended", startedAt);
    }
  }

  // The VOD engine picks up archiving once the `ended` doc lands on QDN
  // (docs/vod-pipeline.md). Poll the stream doc so the dashboard can tell when
  // archiving has *finished* (doc status → `archived`), not just that it started.
  const archiving =
    !live &&
    signaling.state === "published" &&
    signaling.result.doc.status === "ended";

  useEffect(() => {
    if (!archiving || archiveDone || !streamId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const doc = await selectApi().getStream(streamId);
        if (!cancelled && doc?.status === "archived") setArchiveDone(true);
      } catch {
        // A failed read-back just keeps the "Archiving…" state; retry next tick.
      }
    };
    const timer = setInterval(() => void poll(), ARCHIVE_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [archiving, archiveDone, streamId]);

  // Session-average chunk production rate (chunks per minute since start).
  const elapsedMinutes = startedAt
    ? Math.max((Date.now() - startedAt) / 60_000, 1 / 60)
    : undefined;
  const chunkRate =
    stats && elapsedMinutes
      ? Math.round(stats.chunksProduced / elapsedMinutes)
      : undefined;
  const bufferState = stats?.bufferState;

  return (
    <>
      <h1 className="page-title">Broadcaster Dashboard</h1>
      <p className="page-subtitle">
        Manage your live stream and monitor its health.
      </p>

      {archiving && !archiveDone && (
        <section
          className="notice notice--archiving"
          aria-live="polite"
          style={{ maxWidth: 560 }}
        >
          <span className="badge badge--archived">Archiving…</span>
          <span className="muted">
            Stream ended — the VOD engine is finalizing the replay archive on
            QDN.
          </span>
        </section>
      )}

      {archiving && archiveDone && (
        <section
          className="notice notice--ready"
          aria-live="polite"
          style={{ maxWidth: 560 }}
        >
          <span className="badge badge--archived">Archived</span>
          <span className="muted">
            Replay archive published to QDN — available on the Discover page.
          </span>
        </section>
      )}

      <div className="card" style={{ maxWidth: 560, marginBottom: 20 }}>
        <div className="field">
          <label htmlFor="title">Stream title</label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="gaming">Gaming</option>
            <option value="tech">Tech</option>
            <option value="music">Music</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          {live ? (
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => {
                void stopBroadcast();
              }}
            >
              Stop broadcast
            </button>
          ) : (
            <button
              type="button"
              className="btn"
              onClick={() => {
                void startBroadcast();
              }}
            >
              Start broadcast
            </button>
          )}
        </div>
      </div>

      {signaling.state !== "idle" && (
        <section
          className={`notice ${
            signaling.state === "error"
              ? "notice--error"
              : signaling.state === "published"
                ? "notice--success"
                : "notice--archiving"
          }`}
          aria-live="polite"
          style={{ maxWidth: 560 }}
        >
          {signaling.state === "publishing" && (
            <>
              <strong>Publishing metadata…</strong>
              <span className="muted mono">
                {signaling.identifier} · {signaling.status}
              </span>
            </>
          )}

          {signaling.state === "published" && (
            <>
              <strong>Metadata published</strong>
              <div className="notice__meta">
                <span className="mono">{signaling.result.identifier}</span>
                <span>{signaling.result.service}</span>
                <span>publisher: {signaling.result.name}</span>
                <span>status: {signaling.result.doc.status}</span>
              </div>
              <span className="muted">
                Re-published on each lifecycle change (state changes only).
              </span>
            </>
          )}

          {signaling.state === "error" && (
            <>
              <strong>Publish failed</strong>
              <span className="muted">{signaling.message}</span>
            </>
          )}
        </section>
      )}

      {live ? (
        <>
          <div className="stats-row" aria-live="polite">
            <Stat label="Status" value="Live" />
            <Stat label="Stream" value={streamId ?? "—"} />
            <Stat label="Viewers" value={stats?.viewers ?? 0} />
            <Stat
              label="Buffer"
              value={bufferState ?? "—"}
              tone={bufferState ? BUFFER_TONE[bufferState] : "muted"}
            />
            <Stat label="Chunks" value={stats?.chunksProduced ?? 0} />
            <Stat
              label="Chunk rate"
              value={chunkRate !== undefined ? `${chunkRate}/min` : "—"}
            />
            <Stat label="Retransmissions" value={stats?.retransmissions ?? 0} />
          </div>

          <section
            className="card"
            aria-label="Bandwidth"
            style={{ marginBottom: 20 }}
          >
            <div className="stream-card__meta">
              <strong>Bandwidth</strong>
              <span className="mono">
                {stats ? kbpsToMbps(stats.bandwidthKbps) : "—"}
              </span>
              {bandwidthHistory.length > 0 && (
                <span className="muted">{bandwidthHistory.length} samples</span>
              )}
            </div>
            {bandwidthHistory.length > 0 ? (
              <Sparkline
                values={bandwidthHistory}
                label="Bandwidth over time (kbps)"
              />
            ) : (
              <p className="muted" style={{ margin: 0 }}>
                Waiting for the first stats sample…
              </p>
            )}
          </section>
        </>
      ) : archiving ? (
        <div className="stats-row">
          <Stat label="Status" value={archiveDone ? "Archived" : "Archiving"} />
          <Stat label="Stream" value={streamId ?? "—"} />
        </div>
      ) : (
        <div className="stats-row">
          <div className="empty" style={{ width: "100%" }}>
            No broadcast yet — start one to see stream health here.
          </div>
        </div>
      )}
    </>
  );
}
