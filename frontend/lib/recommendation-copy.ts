import type { RecommendationItem, UserSkillMasteryItem } from "@/lib/api";
import { formatScore } from "@/lib/catalog-ui";

export const REASON_COPY: Record<string, { title: string; hint: string }> = {
  weak_skill: { title: "Target gap", hint: "This skill currently needs the most practice." },
  cold_start: { title: "Baseline", hint: "Chosen to establish an initial skill signal." },
  prerequisite_ready: { title: "Prerequisite", hint: "Supporting skills look ready enough to attempt this." },
  prerequisite_blocked: { title: "Prerequisite", hint: "A supporting skill may be holding this back." },
  difficulty_fit: { title: "Difficulty", hint: "Difficulty is aligned with the current signal." },
  novel_problem: { title: "Novelty", hint: "Not already solved." },
  spaced_review: { title: "Spacing", hint: "Enough time has passed to review this skill." },
  primary_skill: { title: "Primary skill", hint: "This problem targets the focus skill directly." },
  supporting_skill: { title: "Supporting skill", hint: "This problem also exercises a related skill." },
};

export type WhyFact = {
  key: string;
  title: string;
  value: string;
  ok: boolean;
};

export function recommendationFacts(
  item: RecommendationItem,
  targetSkill: UserSkillMasteryItem | null
): WhyFact[] {
  const codes = new Set(item.explanation.reason_codes);
  const facts: WhyFact[] = [];

  facts.push({
    key: "target",
    title: "Target gap",
    value: targetSkill
      ? `${targetSkill.skill_name} · ${formatScore(targetSkill.score)}`
      : item.problem.target_skill.name,
    ok: codes.has("weak_skill") || codes.has("cold_start") || Boolean(targetSkill),
  });

  if (codes.has("prerequisite_ready") || codes.has("prerequisite_blocked")) {
    facts.push({
      key: "prereq",
      title: "Prerequisite",
      value: codes.has("prerequisite_ready") ? "Ready" : "May be blocking",
      ok: codes.has("prerequisite_ready"),
    });
  }

  facts.push({
    key: "difficulty",
    title: "Difficulty",
    value: item.problem.difficulty.charAt(0).toUpperCase() + item.problem.difficulty.slice(1),
    ok: true,
  });

  if (codes.has("novel_problem")) {
    facts.push({
      key: "novelty",
      title: "Novelty",
      value: "Not solved before",
      ok: true,
    });
  }

  if (codes.has("spaced_review")) {
    facts.push({
      key: "spacing",
      title: "Spacing",
      value: "Due for review",
      ok: true,
    });
  }

  return facts;
}
