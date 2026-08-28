import { describe, expect, it } from "vitest";

import type { PlacementActionItem, ReadinessGap } from "@/lib/api";
import { placementActionHref, topRankedBlockers } from "@/lib/placement-home";

describe("placementActionHref", () => {
  it("routes DSA and Core CS actions to problems, and assess to assessment", () => {
    const dsa: PlacementActionItem = {
      id: "1",
      action_kind: "dsa_problem",
      title: "T",
      description: "",
      target_dimension: "dsa",
      target_skill: null,
      estimated_effort_minutes: 20,
      score: "1",
      rank: 1,
      why: [],
      reason_codes: [],
      payload: { problem_slug: "pair-sum-lookup" },
      generated_at: "2026-01-01T00:00:00Z",
    };
    const quiz = { ...dsa, action_kind: "cs_quiz" as const, payload: { problem_slug: "txn-acid" } };
    const assess = {
      ...dsa,
      action_kind: "assess_dimension" as const,
      payload: { dimension: "core_cs" },
    };
    expect(placementActionHref(dsa)).toBe("/problems/pair-sum-lookup");
    expect(placementActionHref(quiz)).toBe("/problems/txn-acid");
    expect(placementActionHref(assess)).toBe("/assessment?dimension=core_cs");
  });
});

describe("topRankedBlockers", () => {
  it("preserves backend rank order instead of sorting by raw delta", () => {
    const gaps: ReadinessGap[] = [
      {
        dimension: "core_cs",
        skill_slug: null,
        skill_name: null,
        current: 0.52,
        required: 0.6,
        delta: -0.08,
        status: "below",
        severity: "critical_blocker",
        why: "core",
        rank: 1,
        is_critical: true,
      },
      {
        dimension: "dsa",
        skill_slug: null,
        skill_name: null,
        current: 0.4,
        required: 0.7,
        delta: -0.3,
        status: "below",
        severity: "secondary",
        why: "dsa",
        rank: 2,
        is_critical: false,
      },
    ];
    expect(topRankedBlockers(gaps, 3).map((item) => item.dimension)).toEqual(["core_cs", "dsa"]);
  });
});
