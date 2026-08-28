import { IconCheck, IconX } from "./Icons";
import { confidenceLabel } from "@/lib/catalog-ui";

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="sl-label">{children}</p>;
}

export function Metric({
  value,
  suffix,
  className = "",
}: {
  value: string;
  suffix?: string;
  className?: string;
}) {
  return (
    <p className={`sl-num font-semibold tracking-tight text-ink ${className}`}>
      {value}
      {suffix ? <span className="ml-1 text-sm font-medium text-muted">{suffix}</span> : null}
    </p>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const label = confidenceLabel(confidence);
  const tone =
    label === "High" ? "text-success" : label === "Medium" ? "text-warning" : "text-muted";
  return <span className={`text-xs font-medium ${tone}`}>{label} confidence</span>;
}

export function TrendIndicator({ delta }: { delta: number | null }) {
  if (delta === null) {
    return <span className="text-xs text-muted">No trend yet</span>;
  }
  const pct = `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`;
  const tone = delta > 0 ? "text-success" : delta < 0 ? "text-danger" : "text-muted";
  return <span className={`sl-num text-xs font-semibold ${tone}`}>{pct}</span>;
}

export function MasterySignal({
  value,
  className = "",
}: {
  value: number | null;
  className?: string;
}) {
  const pct = value !== null ? Math.min(100, Math.max(0, value * 100)) : 0;
  return (
    <div className={`relative h-1.5 w-full overflow-hidden rounded-full bg-surface-muted ${className}`}>
      {value !== null ? (
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-accent transition-all duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      ) : (
        <div className="absolute inset-y-0 left-0 w-1/5 rounded-full bg-border" />
      )}
    </div>
  );
}

export function ReasonList({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) return null;
  return (
    <ol className="relative space-y-0 border-l border-border pl-6">
      {reasons.map((reason, index) => (
        <li key={`${index}-${reason}`} className="relative pb-5 last:pb-0">
          <span className="absolute -left-[29px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-background font-mono text-[10px] text-muted">
            {String(index + 1).padStart(2, "0")}
          </span>
          <p className="text-sm leading-relaxed text-ink">{reason}</p>
        </li>
      ))}
    </ol>
  );
}

export function EvidenceItem({
  text,
  polarity,
  meta,
}: {
  text: string;
  polarity: string;
  meta?: string;
}) {
  const isPositive = polarity === "positive";
  const isNegative = polarity === "negative";
  return (
    <div className="flex items-start gap-3 py-3">
      <span
        className={`mt-0.5 shrink-0 ${isPositive ? "text-success" : isNegative ? "text-danger" : "text-muted"}`}
        aria-hidden
      >
        {isPositive ? <IconCheck /> : isNegative ? <IconX /> : (
          <span className="mt-1.5 inline-block h-2 w-2 rounded-full bg-muted-light" />
        )}
      </span>
      <div className="min-w-0">
        <p className="text-sm text-ink">{text}</p>
        {meta ? <p className="mt-0.5 text-xs text-muted">{meta}</p> : null}
      </div>
    </div>
  );
}

export function EvidenceTimeline({
  items,
}: {
  items: { id: string; text: string; polarity: string; meta?: string }[];
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted">No evidence yet.</p>;
  }
  return (
    <div className="divide-y divide-border">
      {items.map((item) => (
        <EvidenceItem key={item.id} text={item.text} polarity={item.polarity} meta={item.meta} />
      ))}
    </div>
  );
}

export function Sparkline({
  values,
  label = "Trend",
}: {
  values: number[];
  label?: string;
}) {
  if (values.length < 2) {
    return <p className="text-sm text-muted">History appears after more attempts.</p>;
  }
  const width = 280;
  const height = 56;
  const pad = 4;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values.map((value, index) => {
    const x = pad + (index / (values.length - 1)) * (width - pad * 2);
    const y = pad + (1 - (value - min) / span) * (height - pad * 2);
    return `${x},${y}`;
  });
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="text-accent" aria-label={label}>
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(" ")}
      />
    </svg>
  );
}
