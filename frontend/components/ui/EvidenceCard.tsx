import { IconCheck, IconX } from "./Icons";

export function EvidenceCard({
  text,
  polarity,
}: {
  text: string;
  polarity: string;
}) {
  const isPositive = polarity === "positive";
  const isNegative = polarity === "negative";

  const styles = isPositive
    ? "border-success/20 bg-success-soft"
    : isNegative
      ? "border-danger/20 bg-danger-soft"
      : "border-border bg-surface-muted";

  const iconColor = isPositive ? "text-success" : isNegative ? "text-danger" : "text-muted";

  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 text-sm ${styles}`}>
      <span className={`mt-0.5 shrink-0 ${iconColor}`}>
        {isPositive ? <IconCheck /> : isNegative ? <IconX /> : <span className="inline-block h-2 w-2 rounded-full bg-muted" />}
      </span>
      <p className="text-ink">{text}</p>
    </div>
  );
}
