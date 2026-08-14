import { Link } from "react-router-dom";
import type { Stream } from "../types";
import StatusBadge from "./StatusBadge";

function thumbHue(streamId: string): number {
  let sum = 0;
  for (const ch of streamId) sum = (sum + ch.charCodeAt(0)) % 360;
  return sum;
}

export default function StreamCard({ stream }: { stream: Stream }) {
  const hue = thumbHue(stream.streamId);

  return (
    <div className="card stream-card">
      <Link
        to={`/watch/${stream.streamId}`}
        className="stream-card__thumb"
        aria-label={`Watch ${stream.title}`}
      >
        {stream.thumbnail ? (
          <img
            src={stream.thumbnail}
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <span
            className="stream-card__placeholder"
            style={{
              background: `linear-gradient(135deg, hsl(${hue} 40% 16%), hsl(${(hue + 50) % 360} 45% 26%))`,
            }}
          >
            <span className="stream-card__category">{stream.category}</span>
          </span>
        )}
      </Link>

      <div className="stream-card__meta">
        <StatusBadge status={stream.status} />
        {stream.viewers > 0 && (
          <span>{stream.viewers.toLocaleString()} watching</span>
        )}
      </div>

      <Link to={`/watch/${stream.streamId}`} className="stream-card__title">
        {stream.title}
      </Link>

      <div className="stream-card__meta">
        <Link to={`/profile/${stream.publisher}`}>{stream.publisher}</Link>
        <span>·</span>
        <span>{stream.category}</span>
      </div>
    </div>
  );
}

