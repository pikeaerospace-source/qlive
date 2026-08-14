import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Player from "../components/Player";
import Stat from "../components/Stat";
import StatusBadge from "../components/StatusBadge";
import { api } from "../data/api";
import type { Stream, StreamStats } from "../types";

export default function WatchPage() {
  const { streamId } = useParams<{ streamId: string }>();
  const [stream, setStream] = useState<Stream>();
  const [stats, setStats] = useState<StreamStats>();
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!streamId) return;
    api.getStream(streamId).then((s) => {
      if (s) setStream(s);
      else setNotFound(true);
    });
    api.getStreamStats(streamId).then(setStats);
  }, [streamId]);

  if (notFound) return <div className="empty">Stream not found.</div>;
  if (!stream) return <div className="empty">Loading…</div>;

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

      <div className="stats-row">
        <Stat label="Viewers" value={stats?.viewers ?? stream.viewers} />
        <Stat
          label="Bitrate"
          value={`${Math.round(
            (stream.bitrate.video + stream.bitrate.audio) / 1000,
          )} kbps`}
        />
        <Stat label="Fragment" value={`${stream.fragmentDurationMs} ms`} />
        <Stat label="Buffer" value={stats?.bufferState ?? "—"} />
      </div>
    </>
  );
}
