import type { PlacementReadiness, ReadinessDimensionItem, ReadinessGap } from "@/lib/api";
import {
  assessedDimensionCoverage,
  confidenceBand,
  criticalDimensionGapCount,
  dimensionGap,
  formatPointsDelta,
  formatScorePercent,
  orderedDimensions,
  placementStateLabel,
  riskLabel,
  unassessedDimensionCount,
} from "@/lib/placement-home";

function MetaStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="sl-label">{label}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  );
}

export function DistanceToReady({
  hasTarget,
  dimensions,
  gaps,
}: {
  hasTarget: boolean;
  dimensions: ReadinessDimensionItem[];
  gaps: ReadinessGap[];
}) {
  if (!hasTarget) {
    return (
      <section aria-labelledby="distance-heading">
        <h2 id="distance-heading" className="sl-label">
          Distance to target
        </h2>
        <p className="mt-2 text-sm text-muted">Choose a target profile to evaluate readiness.</p>
      </section>
    );
  }

  const critical = criticalDimensionGapCount(gaps);
  const unassessed = unassessedDimensionCount(dimensions);
  const rows = orderedDimensions(dimensions).map((dim) => {
    const gap = dimensionGap(gaps, dim.key);
    if (dim.status === "not_assessed") {
      return { key: dim.key, name: dim.display_name, value: "Not assessed", tone: "muted" as const };
    }
    const delta = formatPointsDelta(gap?.delta);
    if (delta) {
      const below = (gap?.delta ?? 0) < 0;
      return {
        key: dim.key,
        name: dim.display_name,
        value: delta,
        tone: below ? ("danger" as const) : ("success" as const),
      };
    }
    if (formatScorePercent(dim.score)) {
      return { key: dim.key, name: dim.display_name, value: "Assessed", tone: "muted" as const };
    }
    return { key: dim.key, name: dim.display_name, value: "Not enough evidence", tone: "muted" as const };
  });

  return (
    <section aria-labelledby="distance-heading">
      <h2 id="distance-heading" className="sl-label">
        Distance to target
      </h2>
      <p className="mt-2 text-sm font-medium">
        {critical === 1 ? "1 critical gap" : `${critical} critical gaps`}
        {unassessed > 0 ? (
          <span className="ml-2 font-normal text-muted">
            · {unassessed} dimension{unassessed === 1 ? "" : "s"} not yet assessed
          </span>
        ) : null}
      </p>
      <ul className="mt-3 space-y-1.5 text-sm">
        {rows.map((row) => (
          <li key={row.key} className="flex items-baseline justify-between gap-4">
            <span>{row.name}</span>
            <span
              className={`sl-num ${
                row.tone === "danger" ? "text-danger" : row.tone === "success" ? "text-success" : "text-muted"
              }`}
            >
              {row.value}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ReadinessExplanation({ sentences }: { sentences: string[] }) {
  if (sentences.length === 0) return null;
  return (
    <section aria-labelledby="why-readiness-heading">
      <h2 id="why-readiness-heading" className="sl-label">
        Why this readiness state?
      </h2>
      <ul className="mt-3 space-y-2">
        {sentences.map((line) => (
          <li key={line} className="text-sm leading-relaxed text-ink">
            {line}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ReadinessHeader({ readiness }: { readiness: PlacementReadiness }) {
  const confidence = confidenceBand(readiness.confidence);
  const coverage = assessedDimensionCoverage(readiness.dimensions);

  return (
    <header className="grid gap-6 border-b border-border pb-6 lg:grid-cols-12">
      <div className="lg:col-span-7">
        <p className="sl-page-kicker">Placement readiness intelligence</p>
        <h1 className="sl-page-title mt-2">Placement readiness</h1>
        {readiness.target ? (
          <p className="mt-2 text-lg font-semibold tracking-tight">{readiness.target.name}</p>
        ) : null}
        <p className="mt-2 max-w-xl text-sm text-muted">
          Signal, interpretation, and the next action — measured against a SkillLens target model, not an employer.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4 lg:col-span-5">
        <MetaStat label="State" value={placementStateLabel(readiness.state)} />
        <MetaStat label="Confidence" value={confidence ?? "—"} />
        <MetaStat
          label="Evidence coverage"
          value={`${coverage.assessed} / ${coverage.total} dimensions assessed`}
        />
      </div>
    </header>
  );
}

export function PlacementRiskPanel({
  risk,
  disclaimer,
}: {
  risk: string;
  disclaimer: string;
}) {
  return (
    <section aria-labelledby="risk-heading">
      <h2 id="risk-heading" className="sl-label">
        Readiness risk
      </h2>
      <p className="mt-2 text-lg font-semibold">{riskLabel(risk)}</p>
      <p className="mt-1 text-xs text-muted">{disclaimer}</p>
    </section>
  );
}
