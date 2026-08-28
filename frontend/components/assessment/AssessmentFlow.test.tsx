import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AssessmentFlow } from "./AssessmentFlow";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAssessmentPlan: vi.fn(),
  getProblem: vi.fn(),
  startAttempt: vi.fn(),
  submitAttempt: vi.fn(),
  getMyMastery: vi.fn(),
  getMyReadiness: vi.fn(),
  getMyGaps: vi.fn(),
  getNextPlacementAction: vi.fn(),
}));

import {
  getAssessmentPlan,
  getCurrentUser,
  getMyGaps,
  getMyMastery,
  getMyReadiness,
  getNextPlacementAction,
  getProblem,
  startAttempt,
  submitAttempt,
} from "@/lib/api";

const user = {
  id: "u1",
  email: "a@b.com",
  display_name: "Manish",
  created_at: "2026-01-01T00:00:00Z",
};

const planItem = {
  position: 1,
  activity_kind: "coding" as const,
  problem_slug: "pair-sum-lookup",
  problem_title: "Pair Sum Lookup",
  dimension: "dsa",
  skill_slug: "arrays",
  skill_name: "Arrays",
  estimated_minutes: 15,
  difficulty: "easy" as const,
};

const plan = {
  assessment_id: "11111111-1111-1111-1111-111111111111",
  state: "ok",
  message: null,
  target: { slug: "product-sde", name: "Product SDE" },
  total_items: 1,
  items: [planItem],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  sessionStorage.clear();
});

describe("AssessmentFlow", () => {
  it("redirects unauthenticated users", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      status: 401,
      error: { detail: "Authentication required", code: "unauthorized" },
    });
    vi.mocked(getAssessmentPlan).mockResolvedValue({
      status: 200,
      data: { assessment_id: null, state: "no_target", message: "", target: null, total_items: 0, items: [] },
    });
    render(<AssessmentFlow />);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?next=%2Fassessment");
    });
  });

  it("starts, progresses, and completes using readiness and placement actions", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ status: 200, data: user });
    vi.mocked(getAssessmentPlan).mockResolvedValue({ status: 200, data: plan });
    vi.mocked(getProblem).mockResolvedValue({
      status: 200,
      data: {
        id: "prob-1",
        slug: "pair-sum-lookup",
        title: "Pair Sum Lookup",
        prompt_md: "Find two numbers that sum to target.",
        difficulty: "easy",
        estimated_minutes: 15,
        hint_count: 1,
        topic: { slug: "t", name: "T", sort_order: 1 },
        skills: [],
        learner_state: null,
        activity_kind: "coding",
      },
    });
    vi.mocked(startAttempt).mockResolvedValue({
      status: 201,
      data: {
        id: "attempt-1",
        problem_id: "prob-1",
        status: "in_progress",
        started_at: "2026-08-26T00:00:00Z",
        submitted_at: null,
        time_spent_seconds: null,
        hints_used_count: 0,
        is_correct: null,
        mistake_type: null,
        code_text: null,
        client_attempt_id: "ap-1",
      },
    });
    vi.mocked(submitAttempt).mockResolvedValue({
      status: 200,
      data: {
        id: "attempt-1",
        problem_id: "prob-1",
        status: "submitted",
        started_at: "2026-08-26T00:00:00Z",
        submitted_at: "2026-08-26T00:05:00Z",
        time_spent_seconds: 30,
        hints_used_count: 0,
        is_correct: true,
        mistake_type: null,
        code_text: null,
        client_attempt_id: "ap-1",
        assessment: { evidence_items: [], mastery_deltas: [], recommendation: null },
      },
    });
    vi.mocked(getMyMastery).mockResolvedValue({
      status: 200,
      data: {
        items: [
          {
            skill_slug: "arrays",
            skill_name: "Arrays",
            topic_slug: null,
            score: "0.7200",
            confidence: "0.4000",
            status: "assessed",
            evidence_count: 1,
            last_attempt_at: "2026-08-26T00:05:00Z",
          },
        ],
      },
    });
    vi.mocked(getMyReadiness).mockResolvedValue({
      status: 200,
      data: {
        target: {
          slug: "product-sde",
          name: "Product SDE",
          description: "",
          disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
        },
        state: "early",
        confidence: 0.3,
        risk: "high",
        dimensions: [
          {
            key: "dsa",
            display_name: "DSA",
            status: "early",
            score: 0.72,
            confidence: 0.4,
            coverage: 0.2,
            assessed_count: 1,
            in_scope_count: 10,
          },
          {
            key: "core_cs",
            display_name: "Core CS",
            status: "not_assessed",
            score: null,
            confidence: null,
            coverage: 0,
            assessed_count: 0,
            in_scope_count: 5,
          },
          {
            key: "projects",
            display_name: "Projects",
            status: "not_assessed",
            score: null,
            confidence: null,
            coverage: 0,
            assessed_count: 0,
            in_scope_count: 0,
          },
        ],
        blockers: [],
        score: null,
        disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
      },
    });
    vi.mocked(getMyGaps).mockResolvedValue({ status: 200, data: { items: [], disclaimer: "" } });
    vi.mocked(getNextPlacementAction).mockResolvedValue({
      status: 200,
      data: {
        state: "ok",
        message: null,
        action: {
          id: "act-1",
          action_kind: "cs_quiz",
          title: "Improve SQL Joins",
          description: "Focused Core CS quiz",
          target_dimension: "core_cs",
          target_skill: { slug: "sql-joins", name: "SQL Joins" },
          estimated_effort_minutes: 10,
          score: "1.0",
          rank: 1,
          why: ["Core CS is below the selected target."],
          reason_codes: ["critical_dimension_gap"],
          payload: { problem_slug: "sql-inner-join-drop" },
          generated_at: "2026-08-26T00:05:00Z",
        },
      },
    });

    render(<AssessmentFlow />);

    expect(await screen.findByTestId("assessment-intro")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Begin" }));

    expect(await screen.findByTestId("assessment-question")).toBeInTheDocument();
    expect(screen.getByTestId("assessment-progress")).toHaveTextContent("Question 1 of 1");
    expect(screen.getByText("Find two numbers that sum to target.")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("I would solve this correctly"));
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => {
      expect(submitAttempt).toHaveBeenCalledWith(
        "attempt-1",
        expect.objectContaining({ is_correct: true })
      );
    });

    expect(await screen.findByTestId("assessment-complete")).toBeInTheDocument();
    expect(screen.getByText("Your initial placement profile")).toBeInTheDocument();
    expect(screen.getByTestId("assessment-next")).toHaveTextContent("Improve SQL Joins");
    expect(getNextPlacementAction).toHaveBeenCalledWith({ refresh: true });
    expect(getMyReadiness).toHaveBeenCalled();
  });
});
