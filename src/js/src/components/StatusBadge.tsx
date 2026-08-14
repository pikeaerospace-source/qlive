import type { StreamStatus } from "../types";

const LABELS: Record<StreamStatus, { text: string; className: string }> = {
  live: { text: "Live", className: "badge badge--live" },
  announced: { text: "Upcoming", className: "badge badge--upcoming" },
  ended: { text: "Ended", className: "badge badge--archived" },
  archived: { text: "Replay", className: "badge badge--archived" },
  interrupted: { text: "Interrupted", className: "badge badge--archived" },
};

export default function StatusBadge({ status }: { status: StreamStatus }) {
  const { text, className } = LABELS[status];
  return <span className={className}>{text}</span>;
}
