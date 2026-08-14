import { useEffect, useState } from "react";
import Stat from "../components/Stat";
import StreamCard from "../components/StreamCard";
import { api } from "../data/api";
import type { Stream } from "../types";

const CATEGORIES = ["all", "gaming", "tech", "music"];

export default function DiscoveryPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [category, setCategory] = useState("all");

  useEffect(() => {
    api.listStreams().then(setStreams);
  }, []);

  const live = streams.filter((s) => s.status === "live");
  const upcoming = streams.filter((s) => s.status === "announced");
  const filtered = streams.filter(
    (s) => category === "all" || s.category === category,
  );

  return (
    <>
      <h1 className="page-title">Discover</h1>
      <p className="page-subtitle">
        Live and upcoming streams on the Qortal network.
      </p>

      <div className="stats-row" style={{ marginBottom: 20 }}>
        <Stat label="Live now" value={live.length} />
        <Stat label="Upcoming" value={upcoming.length} />
        <Stat
          label="Total viewers"
          value={live.reduce((n, s) => n + s.viewers, 0).toLocaleString()}
        />
      </div>

      <div className="stats-row" style={{ marginBottom: 16 }}>
        {CATEGORIES.map((c) => (
          <button
            key={c}
            type="button"
            className="btn btn--ghost"
            style={
              category === c
                ? { borderColor: "var(--accent)", color: "var(--text)" }
                : undefined
            }
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty">No streams in this category.</div>
      ) : (
        <div className="grid">
          {filtered.map((s) => (
            <StreamCard key={s.streamId} stream={s} />
          ))}
        </div>
      )}
    </>
  );
}
