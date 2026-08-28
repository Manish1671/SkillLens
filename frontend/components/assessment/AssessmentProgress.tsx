"use client";

export function AssessmentProgress({
  current,
  total,
  dimension,
}: {
  current: number;
  total: number;
  dimension: string;
}) {
  const label = dimension === "core_cs" ? "Core CS" : "DSA";
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="sl-eyebrow">Assessing your readiness</p>
        <p className="mt-1 text-sm font-medium" data-testid="assessment-dimension">
          {label}
        </p>
      </div>
      <p className="font-mono text-sm text-muted" data-testid="assessment-progress">
        Question {current} of {total}
      </p>
    </div>
  );
}
