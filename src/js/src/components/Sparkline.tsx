/**
 * QLive — inline SVG sparkline.
 *
 * Renders a compact line chart from a numeric series (scaled to its own max)
 * for at-a-glance trends such as bandwidth over time. Decorative and
 * accessible: exposed as an image with the caller's `label`.
 */

export default function Sparkline({
  values,
  width = 480,
  height = 64,
  label,
  className = "sparkline",
}: {
  values: number[];
  width?: number;
  height?: number;
  /** Accessible description (rendered as the image's `aria-label`). */
  label?: string;
  className?: string;
}) {
  if (values.length === 0) return null;

  // Scale to the series max (baseline at zero) so the shape is visible even for
  // a nearly-flat series.
  const max = Math.max(...values, 1);
  const denom = Math.max(values.length - 1, 1);
  const y = (value: number) => height - (value / max) * height;
  const points =
    values.length === 1
      ? // A single sample has no span; draw a flat line across the width.
        `${0},${y(values[0]).toFixed(1)} ${width},${y(values[0]).toFixed(1)}`
      : values
          .map(
            (value, i) =>
              `${((i / denom) * width).toFixed(1)},${y(value).toFixed(1)}`,
          )
          .join(" ");

  return (
    <svg
      className={className}
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label={label ?? "sparkline"}
      data-testid="sparkline"
    >
      <polyline className="sparkline__line" points={points} />
    </svg>
  );
}
