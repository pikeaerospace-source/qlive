import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Stat from "../components/Stat";
import StreamCard from "../components/StreamCard";
import { api } from "../data/api";
import type { Stream, Streamer } from "../types";

export default function ProfilePage() {
  const { name } = useParams<{ name: string }>();
  const [streamer, setStreamer] = useState<Streamer>();
  const [streams, setStreams] = useState<Stream[]>([]);

  useEffect(() => {
    if (!name) return;
    api.getStreamer(name).then(setStreamer);
    api.getStreamerStreams(name).then(setStreams);
  }, [name]);

  if (!streamer) return <div className="empty">Loading…</div>;

  return (
    <>
      <h1 className="page-title">
        {streamer.name}
        {streamer.verified && (
          <span className="badge badge--verified" style={{ marginLeft: 10 }}>
            Verified
          </span>
        )}
      </h1>
      <p className="page-subtitle">{streamer.bio}</p>

      <div className="stats-row" style={{ marginBottom: 20 }}>
        <Stat label="Followers" value={streamer.followers.toLocaleString()} />
        <Stat label="Streams" value={streams.length} />
      </div>

      <h2 className="muted" style={{ fontSize: 16, margin: "0 0 12px" }}>
        Streams
      </h2>
      {streams.length === 0 ? (
        <div className="empty">No streams yet.</div>
      ) : (
        <div className="grid">
          {streams.map((s) => (
            <StreamCard key={s.streamId} stream={s} />
          ))}
        </div>
      )}
    </>
  );
}
