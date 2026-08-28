import type { PlacementReadiness, UserSkillMasteryItem } from "@/lib/api";
import { confidenceBand, formatScorePercent, placementStateLabel } from "@/lib/placement-home";

export function howDidWeAssessYou(input: {
  targetName: string | null;
  dsaAssessed: number;
  csAssessed: number;
  planDsaCount: number;
  planCsCount: number;
}): string[] {
  const target = input.targetName ?? "your selected target";
  return [
    `Your DSA profile is based on ${input.dsaAssessed} assessed skills (${input.planDsaCount} DSA items in this session).`,
    `Core CS is based on ${input.csAssessed} DBMS/SQL skills with evidence (${input.planCsCount} quizzes in this session).`,
    `Projects and Interview have not yet been assessed. This profile is measured against ${target}, not a hiring prediction.`,
  ].slice(0, 3);
}

export function assessmentSummaryCounts(
  mastery: UserSkillMasteryItem[],
  readiness: PlacementReadiness | null,
): {
  dsaEvidence: number;
  csEvidence: number;
  skillsAssessed: number;
  skillsInsufficient: number;
} {
  const dsa = readiness?.dimensions.find((item) => item.key === "dsa");
  const cs = readiness?.dimensions.find((item) => item.key === "core_cs");
  return {
    dsaEvidence: dsa?.assessed_count ?? 0,
    csEvidence: cs?.assessed_count ?? 0,
    skillsAssessed: mastery.filter((item) => item.status === "assessed").length,
    skillsInsufficient: mastery.filter((item) => item.status === "insufficient").length,
  };
}

export function profileHeadline(readiness: PlacementReadiness | null): {
  targetName: string;
  stateLabel: string;
  confidenceLabel: string;
} {
  return {
    targetName: readiness?.target?.name ?? "No target selected",
    stateLabel: placementStateLabel(readiness?.state ?? "not_assessed"),
    confidenceLabel: confidenceBand(readiness?.confidence) ?? "Low",
  };
}

export function dimensionScoreLine(score: number | null, status: string): string {
  const pct = formatScorePercent(score);
  if (pct == null) return placementStateLabel(status);
  return `${pct} · ${placementStateLabel(status)}`;
}
