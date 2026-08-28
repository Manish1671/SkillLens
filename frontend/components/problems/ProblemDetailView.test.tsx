import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import { ProblemDetailView } from "./ProblemDetailView";

describe("ProblemDetailView", () => {
  it("renders loading state initially", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () =>
          new Promise(() => {
            /* never resolves */
          })
      )
    );

    render(<ProblemDetailView slug="pair-sum-lookup" />);
    expect(screen.getByText("Loading problem...")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("renders problem detail after load", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          id: "1",
          slug: "pair-sum-lookup",
          title: "Pair Sum Lookup",
          prompt_md: "Find two numbers.",
          difficulty: "easy",
          estimated_minutes: 20,
          topic: { slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 },
          skills: [{ slug: "hashing", name: "Hashing", weight: "1.0", is_primary: true }],
          hint_count: 2,
          learner_state: null,
        }),
      })
    );

    render(<ProblemDetailView slug="pair-sum-lookup" />);
    expect(await screen.findByRole("heading", { level: 1, name: "Pair Sum Lookup" })).toBeInTheDocument();
    expect(screen.getByText("Find two numbers.")).toBeInTheDocument();
    expect(screen.getByText("Hints available")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("starts attempt and navigates", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          id: "problem-1",
          slug: "pair-sum-lookup",
          title: "Pair Sum Lookup",
          prompt_md: "Find two numbers.",
          difficulty: "easy",
          estimated_minutes: 20,
          topic: { slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 },
          skills: [],
          hint_count: 2,
          learner_state: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: "attempt-99",
          problem_id: "problem-1",
          status: "in_progress",
          started_at: "2026-01-01T00:00:00Z",
          submitted_at: null,
          time_spent_seconds: null,
          hints_used_count: 0,
          is_correct: null,
          mistake_type: null,
          code_text: null,
          client_attempt_id: "client-1",
        }),
      });

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", { randomUUID: () => "client-uuid-1" });

    render(<ProblemDetailView slug="pair-sum-lookup" />);
    const startButton = await screen.findByText("Start solving");
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/problems/pair-sum-lookup/attempt/attempt-99");
    });

    vi.unstubAllGlobals();
  });
});
