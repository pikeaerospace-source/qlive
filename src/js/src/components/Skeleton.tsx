/**
 * QLive — loading skeleton placeholders.
 *
 * Rendered while a page's data is still being fetched so the layout doesn't
 * jump when content arrives. Shapes: `grid` (stream-card grid), `text`
 * (paragraph lines), `detail` (watch-page player + body). Decorative only —
 * hidden from assistive tech, since the page announces loading separately.
 */

export type SkeletonVariant = "grid" | "text" | "detail";

export default function Skeleton({
  variant = "grid",
  count = 6,
}: {
  variant?: SkeletonVariant;
  /** Number of placeholder blocks for `grid`/`text`. */
  count?: number;
}) {
  if (variant === "text") {
    return (
      <div aria-hidden="true" data-testid="skeleton">
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className="skeleton skeleton--text" />
        ))}
      </div>
    );
  }

  if (variant === "detail") {
    return (
      <div aria-hidden="true" data-testid="skeleton">
        <div className="skeleton skeleton--thumb" />
        <div className="skeleton skeleton--title" style={{ marginTop: 16 }} />
        <div className="skeleton skeleton--text" />
        <div className="skeleton skeleton--text" style={{ width: "80%" }} />
      </div>
    );
  }

  return (
    <div className="grid" aria-hidden="true" data-testid="skeleton">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton skeleton--card" />
      ))}
    </div>
  );
}
