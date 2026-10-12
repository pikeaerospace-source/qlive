import { useEffect, useState, useSyncExternalStore } from "react";
import Skeleton from "../components/Skeleton";
import Stat from "../components/Stat";
import StreamCard from "../components/StreamCard";
import { selectApi } from "../data/api";
import { replaySortKey, replayState } from "../data/archive";
import { listFollowing, subscribe } from "../data/follows";
import type { Stream } from "../types";

const CATEGORIES = ["all", "gaming", "tech", "music"];
/** Max cards in the Trending (by viewers) row. */
const TRENDING_LIMIT = 3;

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

/** An editorial row of stream cards (Featured / Trending / Following). */
function StreamSection({
  title,
  subtitle,
  streams,
}: {
  title: string;
  subtitle: string;
  streams: Stream[];
}) {
  return (
    <section style={{ marginBottom: 32 }}>
      <h2 className="section-title">{title}</h2>
      <p className="page-subtitle">{subtitle}</p>
      <div className="grid">
        {streams.map((s) => (
          <StreamCard key={s.streamId} stream={s} />
        ))}
      </div>
    </section>
  );
}

export default function DiscoveryPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [reload, setReload] = useState(0);
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortMode>("live");
  const following = useSyncExternalStore(
    subscribe,
    listFollowing,
    listFollowing,
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(undefined);
    selectApi()
      .listStreams()
      .then((list) => {
        if (cancelled) return;
        setStreams(list);
        setLoading(false);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        setError(cause instanceof Error ? cause.message : String(cause));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  const retry = () => setReload((n) => n + 1);

  const live = streams.filter((s) => s.status === "live");
  const upcoming = streams.filter((s) => s.status === "announced");
  // Finished streams whose archive exists or is on its way to QDN.
  const replays = streams.filter(
    (s) =>
      s.status !== "live" &&
      s.status !== "announced" &&
      replayState(s) !== "none",
  );

  const q = query.trim().toLowerCase();
  const matches = (s: Stream) =>
    (category === "all" || s.category === category) &&
    (!q ||
      s.title.toLowerCase().includes(q) ||
      s.publisher.toLowerCase().includes(q));

  const visible = streams
    .filter((s) => s.status === "live" || s.status === "announced")
    .filter(matches)
    .sort((a, b) => compareStreams(a, b, sort));

  const visibleReplays = replays
    .filter(matches)
    .sort((a, b) => replaySortKey(b) - replaySortKey(a));

  // Editorial rows (featured / trending / following), all honouring the
  // category + search filters above. `featured` and `trending` are disjoint so
  // a promoted stream appears once as a highlight; Trending is capped.
  const discoverable = streams.filter(
    (s) => s.status === "live" || s.status === "announced",
  );
  const featured = discoverable
    .filter((s) => s.featured)
    .filter(matches)
    .sort((a, b) => b.viewers - a.viewers);
  const trending = discoverable
    .filter((s) => s.status === "live" && !s.featured)
    .filter(matches)
    .sort((a, b) => b.viewers - a.viewers)
    .slice(0, TRENDING_LIMIT);
  const followingStreams =
    following.length > 0
      ? discoverable
          .filter((s) => following.includes(s.publisher))
          .filter(matches)
          .sort((a, b) => b.viewers - a.viewers)
      : [];

  if (error) {
    return (
      <>
        <h1 className="page-title">Discover</h1>
        <p className="page-subtitle">
          Live and upcoming streams on the Qortal network.
        </p>
        <section className="notice notice--error" aria-live="polite">
          <strong>Couldn’t load streams</strong>
          <span className="muted">{error}</span>
          <div className="notice__actions">
            <button type="button" className="btn" onClick={retry}>
              Retry
            </button>
          </div>
        </section>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <h1 className="page-title">Discover</h1>
        <p className="page-subtitle">
          Live and upcoming streams on the Qortal network.
        </p>
        <Skeleton variant="grid" />
      </>
    );
  }

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
        <Stat label="Replays" value={replays.length} />
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

      {visible.length === 0 && visibleReplays.length === 0 ? (
        <div className="empty">No streams match your search.</div>
      ) : (
        <>
          {featured.length > 0 && (
            <StreamSection
              title="Featured"
              subtitle="Hand-picked live and upcoming streams."
              streams={featured}
            />
          )}

          {followingStreams.length > 0 && (
            <StreamSection
              title="Following"
              subtitle="Live and upcoming from the streamers you follow."
              streams={followingStreams}
            />
          )}

          {trending.length > 0 && (
            <StreamSection
              title="Trending now"
              subtitle="Live streams with the most viewers."
              streams={trending}
            />
          )}

          {visible.length > 0 && (
            <section style={{ marginBottom: 32 }}>
              <h2 className="section-title">Live &amp; upcoming</h2>
              <p className="page-subtitle">
                Everything that's live now or scheduled.
              </p>
              <div className="grid">
                {visible.map((s) => (
                  <StreamCard key={s.streamId} stream={s} />
                ))}
              </div>
            </section>
          )}

          {visibleReplays.length > 0 && (
            <StreamSection
              title="Recently ended"
              subtitle="Replays archived from finished live streams."
              streams={visibleReplays}
            />
          )}
        </>
      )}
    </>
  );
}
