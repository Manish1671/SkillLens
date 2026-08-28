/** Presentation-only comparison of adjacent SkillAssessmentSnapshot scores. Not a domain regression model. */

export const RECENT_DECLINE_THRESHOLD = 0.08;

export type RecentTrendKind = "rise" | "decline" | "stable" | "none";

export type RecentTrendResult = {
  kind: RecentTrendKind;
  from: number | null;
  to: number | null;
  delta: number | null;
  label: string;
};

export function recentTrendFromSnapshots(
  snapshots: { score: string; computed_at: string }[]
): RecentTrendResult {
  if (snapshots.length < 2) {
    return { kind: "none", from: null, to: null, delta: null, label: "No recent trend yet" };
  }

  const chronological = [...snapshots].sort((a, b) =>
    a.computed_at.localeCompare(b.computed_at)
  );
  const previous = parseFloat(chronological[chronological.length - 2].score);
  const newest = parseFloat(chronological[chronological.length - 1].score);
  if (Number.isNaN(previous) || Number.isNaN(newest)) {
    return { kind: "none", from: null, to: null, delta: null, label: "No recent trend yet" };
  }

  const delta = newest - previous;
  if (delta <= -RECENT_DECLINE_THRESHOLD) {
    return {
      kind: "decline",
      from: previous,
      to: newest,
      delta,
      label: "Recent decline",
    };
  }
  if (delta >= RECENT_DECLINE_THRESHOLD) {
    return {
      kind: "rise",
      from: previous,
      to: newest,
      delta,
      label: "Recent improvement",
    };
  }
  return {
    kind: "stable",
    from: previous,
    to: newest,
    delta,
    label: "Recent trend: stable",
  };
}

export function formatPct(value: number): string {
  return `${Math.round(value * 100)}%`;
}
