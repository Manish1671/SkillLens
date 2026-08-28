import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/catalog-graph", () => ({
  loadCatalogGraph: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getMyReadiness: vi.fn(),
  getMyGaps: vi.fn(),
  getMyMastery: vi.fn(),
  getMyPlacementActions: vi.fn(),
  listAttempts: vi.fn(),
}));

import { HomeDashboard } from "./HomeDashboard";
import {
  getCurrentUser,
  getMyGaps,
  getMyMastery,
  getMyPlacementActions,
  getMyReadiness,
  listAttempts,
  type PlacementActionItem,
  type PlacementReadiness,
  type ReadinessDimensionItem,
  type ReadinessGap,
} from "@/lib/api";
import { loadCatalogGraph } from "@/lib/catalog-graph";

const user = {
  id: "u1",
  email: "a@b.com",
  display_name: "Manish",
  created_at: "2026-01-01T00:00:00Z",
};

const DISCLAIMER =
  "SkillLens target profiles are internal readiness models, not official company hiring requirements.";

const productTarget = {
  slug: "product-sde",
  name: "Product SDE",
  description: "Baseline",
  disclaimer: DISCLAIMER,
};

function dim(
  partial: Partial<ReadinessDimensionItem> & Pick<ReadinessDimensionItem, "key" | "display_name">,
): ReadinessDimensionItem {
  return {
    status: "not_assessed",
    score: null,
    confidence: null,
    coverage: 0,
    assessed_count: 0,
    in_scope_count: 5,
    strongest_skills: [],
    weakest_actionable_skill: null,
    target_min_score: null,
    requirement_status: null,
    ...partial,
  };
}

function allDimensions(overrides: Record<string, Partial<ReadinessDimensionItem>> = {}): ReadinessDimensionItem[] {
  const base: ReadinessDimensionItem[] = [
    dim({ key: "dsa", display_name: "DSA", in_scope_count: 14, ...overrides.dsa }),
    dim({ key: "core_cs", display_name: "Core CS", in_scope_count: 5, ...overrides.core_cs }),
    dim({ key: "projects", display_name: "Projects", in_scope_count: 0, ...overrides.projects }),
    dim({ key: "interview", display_name: "Interview", in_scope_count: 0, ...overrides.interview }),
    dim({ key: "profile", display_name: "Profile", in_scope_count: 0, ...overrides.profile }),
  ];
  return base;
}

function readiness(partial: Partial<PlacementReadiness> = {}): PlacementReadiness {
  return {
    target: productTarget,
    state: "not_assessed",
    confidence: null,
    risk: "medium",
    dimensions: allDimensions(),
    blockers: [],
    score: null,
    disclaimer: DISCLAIMER,
    explanation: ["Choose a target profile to evaluate readiness."],
    risk_disclaimer: "SkillLens model — not a hiring probability.",
    ...partial,
  };
}

function quizAction(): PlacementActionItem {
  return {
    id: "act-quiz",
    action_kind: "cs_quiz",
    title: "Improve SQL Joins",
    description: "A focused Core CS quiz.",
    target_dimension: "core_cs",
    target_skill: { slug: "sql-joins", name: "SQL Joins" },
    estimated_effort_minutes: 8,
    score: "0.8200",
    rank: 1,
    why: [
      "Core CS is currently 8 points below your Product SDE target and is a critical requirement.",
      "Your weakest assessed Core CS skill is SQL Joins.",
      "This quiz is a focused way to improve that gap.",
    ],
    reason_codes: ["critical_dimension_gap", "cs_weak_skill"],
    payload: { problem_slug: "sql-inner-join-drop", dimension: "core_cs" },
    generated_at: "2026-08-27T00:00:00Z",
  };
}

function dsaAction(): PlacementActionItem {
  return {
    id: "act-dsa",
    action_kind: "dsa_problem",
    title: "Pair Sum",
    description: "DSA practice",
    target_dimension: "dsa",
    target_skill: { slug: "hashing", name: "Hashing" },
    estimated_effort_minutes: 20,
    score: "0.6100",
    rank: 1,
    why: ["DSA is below the selected target.", "The DSA recommendation engine selected the coding problem."],
    reason_codes: ["dsa_gap"],
    payload: { problem_slug: "pair-sum-lookup", dimension: "dsa" },
    generated_at: "2026-08-27T00:00:00Z",
  };
}

function assessAction(): PlacementActionItem {
  return {
    id: "act-assess",
    action_kind: "assess_dimension",
    title: "Assess Core CS",
    description: "Not enough evidence",
    target_dimension: "core_cs",
    target_skill: null,
    estimated_effort_minutes: 20,
    score: "0.9000",
    rank: 1,
    why: ["Core CS is required for the selected Product SDE target but there is not enough evidence to determine your current readiness."],
    reason_codes: ["insufficient_evidence"],
    payload: { dimension: "core_cs" },
    generated_at: "2026-08-27T00:00:00Z",
  };
}

const coreCsGap: ReadinessGap = {
  dimension: "core_cs",
  skill_slug: null,
  skill_name: null,
  current: 0.52,
  required: 0.6,
  delta: -0.08,
  status: "below",
  severity: "critical_blocker",
  why: "Coverage is sufficient for an assessment, but current evidence places Core CS below the target requirement.",
  rank: 1,
  is_critical: true,
};

const dsaExceedsGap: ReadinessGap = {
  dimension: "dsa",
  skill_slug: null,
  skill_name: null,
  current: 0.81,
  required: 0.7,
  delta: 0.11,
  status: "exceeds",
  severity: "watch",
  why: "DSA exceeds the target bar.",
  rank: 2,
  is_critical: true,
};

async function renderDashboard() {
  render(<HomeDashboard />);
  await waitFor(() => {
    expect(screen.getByText("Placement readiness")).toBeInTheDocument();
  });
}

beforeEach(() => {
  vi.mocked(getCurrentUser).mockResolvedValue({ status: 200, data: user });
  vi.mocked(getMyMastery).mockResolvedValue({ status: 200, data: { items: [] } });
  vi.mocked(getMyReadiness).mockResolvedValue({
    status: 200,
    data: readiness({ target: null, explanation: ["Choose a target profile to evaluate readiness."] }),
  });
  vi.mocked(listAttempts).mockResolvedValue({
    status: 200,
    data: { items: [], next_cursor: null, has_more: false },
  });
  vi.mocked(getMyPlacementActions).mockResolvedValue({
    status: 200,
    data: { items: [], state: "no_eligible_action", message: null },
  });
  vi.mocked(loadCatalogGraph).mockResolvedValue({ skills: [], edges: [] });
  vi.mocked(getMyGaps).mockResolvedValue({ status: 200, data: { items: [], disclaimer: DISCLAIMER } });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("HomeDashboard command center", () => {
  it("shows choose-target empty state when no target is selected", async () => {
    vi.mocked(getMyPlacementActions).mockResolvedValue({
      status: 200,
      data: { items: [], state: "no_target", message: "Choose a target profile to evaluate placement actions." },
    });
    await renderDashboard();
    expect(screen.getByText("Choose what you're preparing for.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Choose target" }).length).toBeGreaterThan(0);
    expect(screen.queryByText("Product SDE")).not.toBeInTheDocument();
  });

  it("asks for a first assessment when a target has no evidence", async () => {
    vi.mocked(getMyReadiness).mockResolvedValue({
      status: 200,
      data: readiness({
        explanation: ["DSA is not assessed yet.", "Core CS is not assessed yet."],
      }),
    });
    vi.mocked(getMyPlacementActions).mockResolvedValue({
      status: 200,
      data: { items: [assessAction()], state: "ok", message: null },
    });
    await renderDashboard();
    expect(screen.getByText("Product SDE")).toBeInTheDocument();
    expect(screen.getByText("Assess Core CS")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start assessment/ })).toHaveAttribute(
      "href",
      "/assessment?dimension=core_cs",
    );
  });

  it("shows DSA evidence and labels Core CS as not assessed", async () => {
    vi.mocked(getMyReadiness).mockResolvedValue({
      status: 200,
      data: readiness({
        state: "early",
        confidence: 0.45,
        dimensions: allDimensions({
          dsa: {
            status: "ready",
            score: 0.81,
            confidence: 0.55,
            assessed_count: 6,
            coverage: 0.43,
            target_min_score: 0.7,
            requirement_status: "exceeds",
            strongest_skills: [{ skill_slug: "hashing", skill_name: "Hashing", score: 0.86 }],
            weakest_actionable_skill: {
              skill_slug: "sliding-window",
              skill_name: "Sliding Window",
              score: 0.46,
            },
          },
        }),
        explanation: [
          "Your DSA evidence is currently sufficient and above the Product SDE target.",
          "Core CS is not assessed yet.",
          "Projects, Interview, and Profile are not assessed yet.",
        ],
      }),
    });
    vi.mocked(getMyGaps).mockResolvedValue({
      status: 200,
      data: {
        disclaimer: DISCLAIMER,
        items: [
          {
            dimension: "core_cs",
            skill_slug: null,
            skill_name: null,
            current: null,
            required: 0.6,
            delta: null,
            status: "insufficient_evidence",
            severity: "critical_blocker",
            why: "Core CS does not have enough evidence to compare against the target bar.",
            rank: 1,
            is_critical: true,
          },
          dsaExceedsGap,
        ],
      },
    });
    vi.mocked(getMyPlacementActions).mockResolvedValue({
      status: 200,
      data: { items: [assessAction()], state: "ok", message: null },
    });
    await renderDashboard();

    const dsaRow = screen.getByTestId("dimension-dsa");
    const coreRow = screen.getByTestId("dimension-core_cs");
    expect(dsaRow).toHaveTextContent("81%");
    expect(coreRow).toHaveTextContent("Not assessed");
    expect(coreRow).not.toHaveTextContent("0%");
  });

  it("shows DSA strong vs Core CS below target, blockers, explanation, risk, and distance", async () => {
    vi.mocked(getMyReadiness).mockResolvedValue({
      status: 200,
      data: readiness({
        state: "developing",
        confidence: 0.5,
        risk: "high",
        dimensions: allDimensions({
          dsa: {
            status: "ready",
            score: 0.81,
            confidence: 0.55,
            assessed_count: 6,
            coverage: 0.43,
            target_min_score: 0.7,
            requirement_status: "exceeds",
            strongest_skills: [{ skill_slug: "hashing", skill_name: "Hashing", score: 0.86 }],
            weakest_actionable_skill: {
              skill_slug: "sliding-window",
              skill_name: "Sliding Window",
              score: 0.46,
            },
          },
          core_cs: {
            status: "developing",
            score: 0.52,
            confidence: 0.5,
            assessed_count: 4,
            coverage: 0.8,
            target_min_score: 0.6,
            requirement_status: "below",
            strongest_skills: [{ skill_slug: "sql-basics", skill_name: "SQL Basics", score: 0.7 }],
            weakest_actionable_skill: {
              skill_slug: "sql-joins",
              skill_name: "SQL Joins",
              score: 0.42,
            },
          },
        }),
        explanation: [
          "Your DSA evidence is currently sufficient and above the Product SDE target.",
          "Core CS is assessed but remains below the target bar.",
          "Projects, Interview, and Profile are not assessed yet.",
        ],
      }),
    });
    vi.mocked(getMyGaps).mockResolvedValue({
      status: 200,
      data: { disclaimer: DISCLAIMER, items: [coreCsGap, dsaExceedsGap] },
    });
    vi.mocked(getMyPlacementActions).mockResolvedValue({
      status: 200,
      data: { items: [quizAction()], state: "ok", message: null },
    });
    vi.mocked(listAttempts).mockResolvedValue({
      status: 200,
      data: {
        next_cursor: null,
        has_more: false,
        items: [
          {
            id: "a1",
            problem: {
              id: "q1",
              slug: "sql-joins-inner",
              title: "SQL Joins",
              difficulty: "easy",
              activity_kind: "quiz",
            },
            status: "submitted",
            started_at: "2026-08-26T00:00:00Z",
            submitted_at: "2026-08-26T00:10:00Z",
            time_spent_seconds: 90,
            hints_used_count: 0,
            is_correct: true,
            mistake_type: null,
          },
        ],
      },
    });

    await renderDashboard();

    expect(screen.getByText("Product SDE")).toBeInTheDocument();
    expect(screen.getAllByText("Developing").length).toBeGreaterThan(0);
    expect(screen.getAllByText("SkillLens model — not a hiring probability.").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Core CS is assessed but remains below the target bar."),
    ).toBeInTheDocument();
    expect(screen.getByText("Coverage is sufficient for an assessment, but current evidence places Core CS below the target requirement.")).toBeInTheDocument();
    expect(screen.getByText("Critical blocker")).toBeInTheDocument();
    expect(screen.getByText("1 critical gap")).toBeInTheDocument();
    expect(screen.getByText(/2 \/ 5 dimensions assessed/)).toBeInTheDocument();
    expect(screen.getByTestId("dimension-dsa")).toHaveTextContent("MEETS");
    expect(screen.getByTestId("dimension-core_cs")).toHaveTextContent("BELOW");
    expect(screen.getByText("+11 points")).toBeInTheDocument();
    expect(screen.getByText("-8 points")).toBeInTheDocument();

    const projectsRow = screen.getByTestId("dimension-projects");
    const interviewRow = screen.getByTestId("dimension-interview");
    expect(projectsRow).toHaveTextContent("Not assessed");
    expect(interviewRow).toHaveTextContent("Not assessed");
    expect(projectsRow?.textContent).not.toMatch(/0%/);
    expect(interviewRow?.textContent).not.toMatch(/0%/);

    expect(screen.getByRole("link", { name: /Hashing — 86%/ })).toHaveAttribute("href", "/skills/hashing");
    expect(screen.getByRole("link", { name: /SQL Joins — 42%/ })).toHaveAttribute("href", "/skills/sql-joins");
    expect(screen.getByRole("link", { name: "Change target" })).toHaveAttribute("href", "/account");

    expect(screen.getByText("Next Core CS action")).toBeInTheDocument();
    expect(screen.getByText("Improve SQL Joins")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start quiz/ })).toHaveAttribute(
      "href",
      "/problems/sql-inner-join-drop",
    );
    expect(screen.queryByText("Pair Sum")).not.toBeInTheDocument();
    expect(screen.getByText("Quiz completed · SQL Joins")).toBeInTheDocument();
  });

  it("labels a DSA placement action as a DSA problem, not a generic coding dashboard", async () => {
    vi.mocked(getMyReadiness).mockResolvedValue({
      status: 200,
      data: readiness({
        state: "early",
        confidence: 0.45,
        dimensions: allDimensions({
          dsa: {
            status: "ready",
            score: 0.81,
            confidence: 0.55,
            assessed_count: 6,
            coverage: 0.43,
            target_min_score: 0.7,
            requirement_status: "exceeds",
          },
        }),
        explanation: ["Your DSA evidence is currently sufficient and above the Product SDE target."],
      }),
    });
    vi.mocked(getMyPlacementActions).mockResolvedValue({
      status: 200,
      data: { items: [dsaAction()], state: "ok", message: null },
    });
    await renderDashboard();
    expect(screen.getByText("Next DSA problem")).toBeInTheDocument();
    expect(screen.getAllByText("Next best action").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Start/ })).toHaveAttribute("href", "/problems/pair-sum-lookup");
    expect(screen.queryByText("Next best problem")).not.toBeInTheDocument();
  });
});
