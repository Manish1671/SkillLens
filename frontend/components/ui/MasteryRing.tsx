export function MasteryRing({
  value,
  size = 64,
  stroke = 5,
  label,
}: {
  value: number | null;
  size?: number;
  stroke?: number;
  label?: string;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = value !== null ? Math.min(100, Math.max(0, value * 100)) : 0;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="relative inline-flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-muted)"
          strokeWidth={stroke}
        />
        {value !== null ? (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700 ease-out"
          />
        ) : null}
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-ink"
        style={{ fontSize: size * 0.22 }}
      >
        {value !== null ? `${pct.toFixed(0)}%` : "—"}
      </span>
      {label ? <span className="text-xs text-muted">{label}</span> : null}
    </div>
  );
}

export function MasteryBar({
  value,
  className = "",
}: {
  value: number | null;
  className?: string;
}) {
  const pct = value !== null ? Math.min(100, Math.max(0, value * 100)) : 0;

  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-surface-muted ${className}`}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-accent/80 to-accent transition-all duration-700 ease-out"
        style={{ width: value !== null ? `${pct}%` : "0%" }}
      />
    </div>
  );
}
