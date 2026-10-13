/** Optional colour tone for the value (e.g. buffer health). */
export type StatTone = "healthy" | "warning" | "danger" | "muted";

export default function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: StatTone;
}) {
  return (
    <div className="stat">
      <span className="stat__label">{label}</span>
      <span className={`stat__value${tone ? ` stat__value--${tone}` : ""}`}>
        {value}
      </span>
    </div>
  );
}
