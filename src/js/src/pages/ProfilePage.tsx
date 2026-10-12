import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Skeleton from "../components/Skeleton";
import Stat from "../components/Stat";
import StreamCard from "../components/StreamCard";
import { selectApi } from "../data/api";
import type { Stream, Streamer } from "../types";

export default function ProfilePage() {
  const { name } = useParams<{ name: string }>();
  const [streamer, setStreamer] = useState<Streamer>();
  const [streams, setStreams] = useState<Stream[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string>();
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!name) return;
    let cancelled = false;
    setError(undefined);
    setNotFound(false);
    const api = selectApi();
    api
      .getStreamer(name)
      .then((s) => {
        if (cancelled) return;
        if (s) setStreamer(s);
        else setNotFound(true);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : String(cause));
      });
    api.getStreamerStreams(name).then((list) => {
      if (!cancelled) setStreams(list);
    });
    return () => {
      cancelled = true;
    };
  }, [name, reload]);

  if (error) {
    return (
      <>
        <h1 className="page-title">{name}</h1>
        <section className="notice notice--error" aria-live="polite">
          <strong>Couldn’t load this profile</strong>
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

  if (notFound) return <div className="empty">Streamer not found.</div>;
  if (!streamer) {
    return (
      <>
        <div className="skeleton skeleton--title" data-testid="skeleton" />
        <Skeleton variant="text" count={3} />
        <Skeleton variant="grid" count={4} />
      </>
    );
  }

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
