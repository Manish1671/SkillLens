import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SkillDetailPageContent } from "./SkillDetailPageContent";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getMySkillDetail: vi.fn(),
  getNextRecommendation: vi.fn(),
}));

import { getCurrentUser, getMySkillDetail, getNextRecommendation } from "@/lib/api";

const user = {
  id: "u1",
  email: "a@b.com",
  display_name: "Manish",
  created_at: "2026-01-01T00:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SkillDetailPageContent", () => {
  it("redirects unauthenticated users", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      status: 401,
      error: { detail: "Authentication required", code: "unauthorized" },
    });
    render(<SkillDetailPageContent slug="sliding-window" />);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?next=%2Fskills%2Fsliding-window");
    });
  });

  it("renders mastery vs confidence and evidence timeline", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ status: 200, data: user });
    vi.mocked(getMySkillDetail).mockResolvedValue({
      status: 200,
      data: {
        slug: "sliding-window",
        name: "Sliding Window",
        description: "Windows over arrays",
        topic_slug: null,
        score: "0.4600",
        confidence: "0.5500",
        status: "assessed",
        evidence_count: 3,
        last_attempt_at: "2026-08-26T00:00:00Z",
        prerequisites: [
          {
            skill_slug: "two-pointers",
            skill_name: "Two Pointers",
            topic_slug: null,
            score: "0.7400",
            confidence: "0.8000",
            status: "assessed",
            evidence_count: 6,
            last_attempt_at: "2026-08-20T00:00:00Z",
          },
        ],
        dependents: [],
        evidence_timeline: [
          {
            id: "e1",
            evidence_type: "solved_without_hints",
            polarity: "positive",
            strength: "0.7",
            summary_text: "Solved Medium problem without hints",
            created_at: "2026-08-26T00:00:00Z",
            attempt_id: "a1",
            details: {},
          },
        ],
        snapshots: [
          { score: "0.7200", confidence: "0.6", computed_at: "2026-08-01T00:00:00Z", attempt_id: "a0" },
          { score: "0.4600", confidence: "0.55", computed_at: "2026-08-26T00:00:00Z", attempt_id: "a1" },
        ],
      },
    });
    vi.mocked(getNextRecommendation).mockResolvedValue({
      status: 200,
      data: {
        recommendation: {
          id: "r1",
          rank: 1,
          score: "1",
          generated_at: "2026-08-26T00:00:00Z",
          source_attempt_id: null,
          problem: {
            id: "p1",
            slug: "longest-unique-substring",
            title: "Longest Unique Substring",
            difficulty: "medium",
            estimated_minutes: 25,
            skills: [],
            target_skill: { slug: "sliding-window", name: "Sliding Window", weight: "1", is_primary: true },
          },
          explanation: {
            target_skill: "sliding-window",
            reason_codes: ["weak_skill", "prerequisite_ready", "difficulty_fit", "novel_problem"],
            score_components: { weak: 0.4123 },
            sentences: ["Sliding Window is a weak actionable skill."],
          },
        },
        target_skill: {
          skill_slug: "sliding-window",
          skill_name: "Sliding Window",
          topic_slug: null,
          score: "0.4600",
          confidence: "0.5500",
          status: "assessed",
          evidence_count: 3,
          last_attempt_at: "2026-08-26T00:00:00Z",
        },
        state: "ok",
        message: null,
      },
    });

    render(<SkillDetailPageContent slug="sliding-window" />);

    expect(await screen.findByTestId("skill-report")).toBeInTheDocument();
    expect(screen.getByText("46% mastery")).toBeInTheDocument();
    expect(screen.getByText("Medium confidence")).toBeInTheDocument();
    expect(screen.getByText("What the evidence says")).toBeInTheDocument();
    expect(screen.getByText("What does the evidence suggest?")).toBeInTheDocument();
    expect(screen.getByText("How strongly should we trust the assessment?")).toBeInTheDocument();
    expect(screen.getByTestId("skill-evidence-timeline")).toHaveTextContent(
      "Solved Medium problem without hints"
    );
    expect(screen.getByText("Recent decline")).toBeInTheDocument();
    expect(screen.getByText(/74% ✓ Ready/)).toBeInTheDocument();
    expect(screen.getByTestId("why-recommendation")).toHaveTextContent("Why SkillLens chose this");
    expect(screen.queryByText("0.4123")).not.toBeInTheDocument();
  });
});
