import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SkillsPageContent } from "./SkillsPageContent";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
}));

vi.mock("@/lib/catalog-graph", () => ({
  loadCatalogGraph: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getMyMastery: vi.fn(),
  getNextRecommendation: vi.fn(),
}));

import { getCurrentUser, getMyMastery, getNextRecommendation } from "@/lib/api";
import { loadCatalogGraph } from "@/lib/catalog-graph";

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

describe("SkillsPageContent", () => {
  beforeEach(() => {
    mockReplace.mockReset();
  });

  it("redirects unauthenticated users to login with next=/skills", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      status: 401,
      error: { detail: "Authentication required", code: "unauthorized" },
    });

    render(<SkillsPageContent />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login?next=%2Fskills");
    });
    expect(screen.queryByText("Authentication required")).not.toBeInTheDocument();
    expect(screen.queryByTestId("skill-profile")).not.toBeInTheDocument();
  });

  it("renders an intentional empty skill profile", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ status: 200, data: user });
    vi.mocked(getMyMastery).mockResolvedValue({ status: 200, data: { items: [] } });
    vi.mocked(getNextRecommendation).mockResolvedValue({
      status: 200,
      data: { recommendation: null, target_skill: null, state: "cold_start", message: null },
    });
    vi.mocked(loadCatalogGraph).mockResolvedValue({
      skills: [
        {
          slug: "arrays",
          name: "Arrays",
          description: "Foundational",
          topic_slug: "arrays-and-hashing",
          is_foundational: true,
          sort_order: 10,
          prerequisite_skill_ids: [],
        },
      ],
      edges: [],
    });

    render(<SkillsPageContent />);

    expect(await screen.findByTestId("skill-profile")).toBeInTheDocument();
    expect(screen.getByText("Your Skill Profile")).toBeInTheDocument();
    expect(screen.getByTestId("skills-empty-onboarding")).toHaveTextContent(
      "Your skill model starts with your first attempt."
    );
    expect(screen.getAllByText("Evidence needed").length).toBeGreaterThan(0);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.getByTestId("skill-map")).toBeInTheDocument();
  });

  it("renders an assessed skill profile with mastery and confidence", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ status: 200, data: user });
    vi.mocked(getMyMastery).mockResolvedValue({
      status: 200,
      data: {
        items: [
          {
            skill_slug: "sliding-window",
            skill_name: "Sliding Window",
            topic_slug: "arrays-and-hashing",
            score: "0.4600",
            confidence: "0.5500",
            status: "assessed",
            evidence_count: 4,
            last_attempt_at: "2026-08-26T00:00:00Z",
          },
        ],
      },
    });
    vi.mocked(getNextRecommendation).mockResolvedValue({
      status: 200,
      data: {
        recommendation: null,
        target_skill: {
          skill_slug: "sliding-window",
          skill_name: "Sliding Window",
          topic_slug: null,
          score: "0.4600",
          confidence: "0.5500",
          status: "assessed",
          evidence_count: 4,
          last_attempt_at: "2026-08-26T00:00:00Z",
        },
        state: "ok",
        message: null,
      },
    });
    vi.mocked(loadCatalogGraph).mockResolvedValue({
      skills: [
        {
          slug: "sliding-window",
          name: "Sliding Window",
          description: "",
          topic_slug: null,
          is_foundational: false,
          sort_order: 40,
          prerequisite_skill_ids: [],
        },
      ],
      edges: [],
    });

    render(<SkillsPageContent />);

    expect(await screen.findByTestId("skill-card-sliding-window")).toBeInTheDocument();
    expect(screen.getAllByText(/46%\s*mastery/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Medium confidence").length).toBeGreaterThan(0);
    expect(screen.getByText("Current focus")).toBeInTheDocument();
    expect(screen.getAllByText("Sliding Window").length).toBeGreaterThan(0);
  });
});
