import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import Player from "../components/Player";
import Skeleton from "../components/Skeleton";
import Stat from "../components/Stat";
import StatusBadge from "../components/StatusBadge";
import { selectApi } from "../data/api";
import {
  formatBytes,
  formatDuration,
  replayLabel,
  replayState,
} from "../data/archive";
import type { Stream, StreamStats } from "../types";

export default function WatchPage() {
  const { streamId } = useParams<{ streamId: string }>();
  const [stream, setStream] = useState<Stream>();
  const [stats, setStats] = useState<StreamStats>();
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string>();
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!streamId) return;
    let cancelled = false;
    setError(undefined);
    setNotFound(false);
    selectApi()
      .getStream(streamId)
      .then((s) => {
        if (cancelled) return;
        if (s) setStream(s);
        else setNotFound(true);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : String(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [streamId, reload]);

  // Live stats only exist while broadcasting; a replay is a static archive.
  useEffect(() => {
    if (!streamId || stream?.status !== "live") return;
    return selectApi().subscribeStats(streamId, setStats);
  }, [streamId, stream?.status]);

  if (error) {
    return (
      <>
        <Link to="/" className="btn btn--ghost" style={{ marginBottom: 12 }}>
          ← Back
        </Link>
        <section className="notice notice--error" aria-live="polite">
          <strong>Couldn’t load this stream</strong>
          <span className="muted">{error}</span>
          <div className="notice__actions">
            <button
              type="button"
              className="btn"
              onClick={() => setReload((n) => n + 1)}
            >
              Retry
            </button>
          </div>
        </section>
      </>
    );
  }

  if (notFound) return <div className="empty">Stream not found.</div>;
  if (!stream) {
    return (
      <>
        <Link to="/" className="btn btn--ghost" style={{ marginBottom: 12 }}>
          ← Back
        </Link>
        <Skeleton variant="detail" />
      </>
    );
  }

  const isLive = stream.status === "live";
  const replay = replayState(stream);
  const archive = stream.archive;
  const kbps = Math.round((stream.bitrate.video + stream.bitrate.audio) / 1000);

  return (
    <>
      <Link to="/" className="btn btn--ghost" style={{ marginBottom: 12 }}>
        ← Back
      </Link>

      <Player stream={stream} />

      <h1 className="page-title" style={{ marginTop: 16 }}>
        {stream.title}
      </h1>
      <div className="stream-card__meta" style={{ marginBottom: 16 }}>
        <StatusBadge status={stream.status} />
        <Link to={`/profile/${stream.publisher}`}>{stream.publisher}</Link>
        <span>·</span>
        <span>{stream.category}</span>
        <span>·</span>
        <span>
          {stream.resolution.width}×{stream.resolution.height} @{" "}
          {stream.resolution.fps}fps
        </span>
      </div>

      <p className="muted">{stream.description}</p>

      {replay !== "none" && (
        <section className={`notice notice--${replay}`} aria-live="polite">
          {replay === "archiving" ? (
            <>
              <strong>{replayLabel(replay)}</strong>
              <span className="muted">
                This stream has ended. Its replay will appear here once the
                archive has been published to QDN.
              </span>
            </>
          ) : (
            <>
              <strong>
                {replay === "partial" ? "Partial replay" : "Replay available"}
              </strong>
              <span className="muted">
                Playing the archived live fragments — no re-encoding.
              </span>
              <div className="notice__meta">
                {archive?.durationMs !== undefined && (
                  <span>Duration {formatDuration(archive.durationMs)}</span>
                )}
                {archive?.sizeBytes !== undefined && (
                  <span>Size {formatBytes(archive.sizeBytes)}</span>
                )}
                {archive?.fragmentCount !== undefined && (
                  <span>
                    {archive.fragmentCount.toLocaleString()} fragments
                  </span>
                )}
              </div>
              {replay === "partial" && (
                <span className="muted">
                  The stream was interrupted, so the replay is incomplete.
                </span>
              )}
              {stream.playbackUrl ? (
                <div className="notice__actions">
                  <a className="btn" href={stream.playbackUrl}>
                    {replayLabel(replay)}
                  </a>
                  <span className="muted">Served from QDN</span>
                </div>
              ) : (
                <span className="muted">
                  Replay source unavailable in mock/offline mode.
                </span>
              )}
            </>
          )}
        </section>
      )}

      <div className="stats-row">
        {isLive ? (
          <>
            <div aria-live="polite">
              <Stat label="Viewers" value={stats?.viewers ?? stream.viewers} />
            </div>
            <Stat label="Bitrate" value={`${kbps} kbps`} />
            <Stat label="Fragment" value={`${stream.fragmentDurationMs} ms`} />
            <Stat label="Buffer" value={stats?.bufferState ?? "—"} />
            <Stat label="Chunks" value={stats?.chunksProduced ?? "—"} />
          </>
        ) : (
          <>
            {archive?.durationMs !== undefined && (
              <Stat
                label="Duration"
                value={formatDuration(archive.durationMs)}
              />
            )}
            {archive?.sizeBytes !== undefined && (
              <Stat
                label="Archive size"
                value={formatBytes(archive.sizeBytes)}
              />
            )}
            {archive?.fragmentCount !== undefined && (
              <Stat
                label="Fragments"
                value={archive.fragmentCount.toLocaleString()}
              />
            )}
            <Stat label="Bitrate" value={`${kbps} kbps`} />
          </>
        )}
      </div>

      {isLive && (
        <div style={{ maxWidth: 560, marginTop: 24 }}>
          <ChatPanel streamId={stream.streamId} />
        </div>
      )}
    </>
  );
}
