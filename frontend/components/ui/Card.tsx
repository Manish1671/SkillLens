export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div className={`sl-card p-5 ${hover ? "sl-card-hover" : ""} ${className}`}>
      {children}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  subtext,
  className = "",
}: {
  label: string;
  value: string;
  subtext?: string;
  className?: string;
}) {
  return (
    <div className={`sl-card p-4 ${className}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight text-ink">{value}</p>
      {subtext ? <p className="mt-1 text-sm text-muted">{subtext}</p> : null}
    </div>
  );
}
