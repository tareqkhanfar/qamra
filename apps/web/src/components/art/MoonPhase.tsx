/** Moon-phase progress (design part `Moon`): p = 0 (new) … 1 (full); lit side on the right. */

export function MoonPhase({
  p,
  lit = "#F2B33D",
  dark = "#22306A",
  className = "size-10",
  label,
}: {
  p: number;
  lit?: string;
  dark?: string;
  className?: string;
  label?: string;
}) {
  const v = Math.max(0, Math.min(1, p));
  const r = 17;
  const rx = (r * Math.abs(1 - 2 * v)).toFixed(2);
  const sweep = v > 0.5 ? 1 : 0;
  const d = v <= 0.001 ? "" : `M20 3 A${r} ${r} 0 0 1 20 37 A${rx} ${r} 0 0 ${sweep} 20 3 Z`;
  return (
    <svg
      viewBox="0 0 40 40"
      className={className}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <circle cx="20" cy="20" r="17" fill={dark} stroke={lit} strokeWidth="1.5" strokeOpacity="0.55" />
      {d && <path d={d} fill={lit} />}
    </svg>
  );
}
