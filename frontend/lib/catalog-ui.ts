import type { SkillSummary, UserSkillMasteryItem } from "@/lib/api";

export const CORE_CS_TOPIC_SLUG = "core-cs-dbms";

export type Difficulty = "easy" | "medium" | "hard";

export type SkillCategory = "strong" | "developing" | "needs_attention" | "insufficient";

export const DIFFICULTY_OPTIONS: { value: Difficulty | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

export function difficultyLabel(difficulty: Difficulty): string {
  return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
}

export function difficultyClasses(difficulty: Difficulty): string {
  switch (difficulty) {
    case "easy":
      return "bg-success-soft text-success";
    case "medium":
      return "bg-warning-soft text-warning";
    case "hard":
      return "bg-danger-soft text-danger";
  }
}

export function formatMinutes(minutes: number): string {
  return `${minutes} min`;
}

export function confidenceLabel(confidence: string): "Low" | "Medium" | "High" {
  const value = parseFloat(confidence);
  if (value >= 0.7) return "High";
  if (value >= 0.4) return "Medium";
  return "Low";
}

export function formatScore(score: string | null): string {
  if (score === null) return "Not enough evidence yet";
  return `${(parseFloat(score) * 100).toFixed(0)}%`;
}

export function scoreValue(score: string | null): number | null {
  if (score === null) return null;
  return parseFloat(score);
}

export function formatDelta(delta: string | null): string {
  if (!delta) return "";
  const value = parseFloat(delta) * 100;
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function snapshotDelta(snapshots: { score: string }[]): number | null {
  if (snapshots.length < 2) return null;
  const oldest = parseFloat(snapshots[snapshots.length - 1].score);
  const newest = parseFloat(snapshots[0].score);
  if (Number.isNaN(oldest) || Number.isNaN(newest)) return null;
  return newest - oldest;
}

export function categorizeSkill(item: UserSkillMasteryItem): SkillCategory {
  if (item.status !== "assessed" || item.score === null) return "insufficient";
  const score = parseFloat(item.score);
  if (score >= 0.7) return "strong";
  if (score >= 0.4) return "developing";
  return "needs_attention";
}

export const CATEGORY_LABELS: Record<SkillCategory, string> = {
  strong: "Strong",
  developing: "Developing",
  needs_attention: "Needs attention",
  insufficient: "Not enough evidence",
};

/** Matches the domain prerequisite-ready threshold for presentation only. */
export const PREREQUISITE_READY_THRESHOLD = 0.45;

export function isPrerequisiteReady(score: string | null, status?: string): boolean {
  if (status && status !== "assessed") return false;
  if (score === null) return false;
  const value = parseFloat(score);
  return !Number.isNaN(value) && value >= PREREQUISITE_READY_THRESHOLD;
}

export function mergeSkillProfile(
  catalog: SkillSummary[],
  masteryItems: UserSkillMasteryItem[]
): UserSkillMasteryItem[] {
  const bySlug = new Map(masteryItems.map((item) => [item.skill_slug, item]));
  if (catalog.length === 0) return masteryItems;
  return catalog.map(
    (skill) =>
      bySlug.get(skill.slug) ?? {
        skill_slug: skill.slug,
        skill_name: skill.name,
        topic_slug: skill.topic_slug,
        score: null,
        confidence: "0.0000",
        status: "insufficient" as const,
        evidence_count: 0,
        last_attempt_at: null,
      }
  );
}

export function isCoreCsSkill(topicSlug: string | null | undefined): boolean {
  return topicSlug === CORE_CS_TOPIC_SLUG;
}

export function skillVisualCategory(input: {
  score?: string | null;
  status?: string;
}): SkillCategory {
  if (input.status !== "assessed" || input.score == null) return "insufficient";
  const score = parseFloat(input.score);
  if (score >= 0.7) return "strong";
  if (score >= 0.4) return "developing";
  return "needs_attention";
}
