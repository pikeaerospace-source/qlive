import { useEffect, useState } from "react";
import Stat from "../components/Stat";
import StreamCard from "../components/StreamCard";
import { api } from "../data/api";
import type { Stream } from "../types";

const CATEGORIES = ["all", "gaming", "tech", "music"];

type SortMode = "live" | "viewers" | "newest";

const STATUS_RANK: Record<Stream["status"], number> = {
  live: 0,
  announced: 1,
  interrupted: 2,
  ended: 2,
  archived: 2,
};

function compareStreams(a: Stream, b: Stream, sort: SortMode): number {
  if (sort === "viewers") return b.viewers - a.viewers;
  if (sort === "newest") return b.startedAt - a.startedAt;
  const rank = STATUS_RANK[a.status] - STATUS_RANK[b.status];
  if (rank !== 0) return rank;
  return b.viewers - a.viewers;
}

export default function DiscoveryPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("live");

  useEffect(() => {
    api.listStreams().then(setStreams);
  }, []);

  const live = streams.filter((s) => s.status === "live");
  const upcoming = streams.filter((s) => s.status === "announced");

  const q = query.trim().toLowerCase();
  const visible = streams
    .filter((s) => category === "all" || s.category === category)
    .filter(
      (s) =>
        !q ||
        s.title.toLowerCase().includes(q) ||
        s.publisher.toLowerCase().includes(q),
    )
    .sort((a, b) => compareStreams(a, b, sort));

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

      <div className="toolbar">
        <div className="toolbar__chips">
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
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>

        <div className="toolbar__controls">
          <input
            type="search"
            className="search"
            placeholder="Search streams…"
            aria-label="Search streams"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <label className="sort">
            <span>Sort</span>
            <select
              aria-label="Sort streams"
              value={sort}
              onChange={(e) => setSort(e.target.value as SortMode)}
            >
              <option value="live">Live first</option>
              <option value="viewers">Most viewers</option>
              <option value="newest">Newest</option>
            </select>
          </label>
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="empty">No streams match your search.</div>
      ) : (
        <div className="grid">
          {visible.map((s) => (
            <StreamCard key={s.streamId} stream={s} />
          ))}
        </div>
      )}
    </>
  );
}

