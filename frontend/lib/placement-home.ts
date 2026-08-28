import type { PlacementActionItem, ReadinessDimensionItem, ReadinessGap } from "@/lib/api";

const STATE_LABELS: Record<string, string> = {
  not_assessed: "Not assessed",
  early: "Early",
  developing: "Developing",
  near_ready: "Near ready",
  ready: "Ready",
};

const RISK_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical_blocker: "Critical blocker",
  secondary: "Secondary",
  watch: "Watch",
};

const DIMENSION_ORDER = ["dsa", "core_cs", "projects", "interview", "profile"];

export function placementStateLabel(state: string): string {
  return STATE_LABELS[state] ?? state.replaceAll("_", " ");
}

export function dimensionStatusLabel(status: string): string {
  return placementStateLabel(status);
}

export function riskLabel(risk: string): string {
  return RISK_LABELS[risk] ?? risk.replaceAll("_", " ");
}

export function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? severity.replaceAll("_", " ");
}

export function confidenceBand(value: number | null | undefined): "Low" | "Medium" | "High" | null {
  if (value == null) return null;
  if (value >= 0.7) return "High";
  if (value >= 0.4) return "Medium";
  return "Low";
}

export function formatScorePercent(score: number | null | undefined): string | null {
  if (score == null) return null;
  return `${Math.round(score * 100)}%`;
}

export function formatPointsDelta(delta: number | null | undefined): string | null {
  if (delta == null) return null;
  const pts = Math.round(delta * 100);
  const sign = pts > 0 ? "+" : "";
  return `${sign}${pts} points`;
}

export function isGapBlocker(gap: ReadinessGap): boolean {
  return (
    gap.status === "below" ||
    gap.status === "insufficient_evidence" ||
    gap.severity === "critical_blocker"
  );
}

export function topRankedBlockers(gaps: ReadinessGap[], limit = 3): ReadinessGap[] {
  return gaps.filter(isGapBlocker).slice(0, limit);
}

export function placementActionHref(action: PlacementActionItem): string {
  if (action.action_kind === "dsa_problem" || action.action_kind === "cs_quiz") {
    const slug = action.payload.problem_slug;
    return typeof slug === "string" ? `/problems/${slug}` : "/problems";
  }
  const dimension =
    (typeof action.payload.dimension === "string" && action.payload.dimension) ||
    action.target_dimension;
  return `/assessment?dimension=${dimension}`;
}

export function placementActionLabel(kind: string): string {
  if (kind === "dsa_problem") return "Next DSA problem";
  if (kind === "cs_quiz") return "Next Core CS action";
  return "Next best action";
}

export function dimensionGap(
  gaps: ReadinessGap[],
  key: string,
): ReadinessGap | undefined {
  return gaps.find((gap) => gap.dimension === key && gap.skill_slug == null);
}

export function orderedDimensions(dimensions: ReadinessDimensionItem[]): ReadinessDimensionItem[] {
  return [...dimensions].sort(
    (a, b) => DIMENSION_ORDER.indexOf(a.key) - DIMENSION_ORDER.indexOf(b.key),
  );
}

export function criticalDimensionGapCount(gaps: ReadinessGap[]): number {
  return gaps.filter(
    (gap) =>
      gap.skill_slug == null &&
      Boolean(gap.is_critical) &&
      (gap.status === "below" || gap.status === "insufficient_evidence"),
  ).length;
}

export function assessedDimensionCoverage(dimensions: ReadinessDimensionItem[]): {
  assessed: number;
  total: number;
} {
  return {
    assessed: dimensions.filter((item) => item.status !== "not_assessed").length,
    total: dimensions.length,
  };
}

export function unassessedDimensionCount(dimensions: ReadinessDimensionItem[]): number {
  return dimensions.filter((item) => item.status === "not_assessed").length;
}

export function matrixStateLabel(dim: ReadinessDimensionItem): string {
  if (dim.status === "not_assessed" || dim.score == null) return "NOT ASSESSED";
  if (dim.requirement_status === "below") return "BELOW";
  if (dim.requirement_status === "meets" || dim.requirement_status === "exceeds") return "MEETS";
  return dimensionStatusLabel(dim.status).toUpperCase();
}

export function dimensionDisplayName(key: string): string {
  const names: Record<string, string> = {
    dsa: "DSA",
    core_cs: "Core CS",
    projects: "Projects",
    interview: "Interview",
    profile: "Profile",
  };
  return names[key] ?? key.replaceAll("_", " ");
}

export function pickSkillSignals(dimensions: ReadinessDimensionItem[]): {
  strongest: { skill_slug: string; skill_name: string; score: number } | null;
  weakest: { skill_slug: string; skill_name: string; score: number } | null;
} {
  const assessed = dimensions.filter((item) => item.key === "dsa" || item.key === "core_cs");
  const strongest = assessed
    .flatMap((item) => item.strongest_skills ?? [])
    .sort((a, b) => b.score - a.score)[0];
  const weakest = assessed
    .map((item) => item.weakest_actionable_skill)
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .sort((a, b) => a.score - b.score)[0];
  return { strongest: strongest ?? null, weakest: weakest ?? null };
}
