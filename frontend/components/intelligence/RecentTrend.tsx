import { formatPct, type RecentTrendResult } from "@/lib/recent-trend";

export function RecentTrend({ trend }: { trend: RecentTrendResult }) {
  if (trend.kind === "none") {
    return <p className="text-xs text-muted">{trend.label}</p>;
  }

  const tone =
    trend.kind === "decline"
      ? "text-warning"
      : trend.kind === "rise"
        ? "text-success"
        : "text-muted";

  return (
    <div className="space-y-1" data-testid="recent-trend">
      <p className={`text-sm font-medium ${tone}`}>{trend.label}</p>
      {trend.from !== null && trend.to !== null ? (
        <p className="sl-num text-xs text-muted">
          {formatPct(trend.from)} → {formatPct(trend.to)}
        </p>
      ) : null}
      {trend.kind === "decline" ? (
        <p className="text-xs text-muted">Recent performance is trending down.</p>
      ) : null}
    </div>
  );
}
