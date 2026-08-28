import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AttemptPageContent } from "./AttemptPageContent";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const attemptDetail = {
  attempt: {
    id: "attempt-1",
    problem_id: "problem-1",
    status: "in_progress" as const,
    started_at: "2026-01-01T00:00:00Z",
    submitted_at: null,
    time_spent_seconds: null,
    hints_used_count: 0,
    is_correct: null,
    mistake_type: null,
    code_text: null,
    client_attempt_id: "client-1",
  },
  problem: {
    id: "problem-1",
    slug: "pair-sum-lookup",
    title: "Pair Sum Lookup",
    difficulty: "easy" as const,
    prompt_md: "Find two numbers.",
    hint_count: 2,
  },
  events: [{ id: "e1", event_type: "started", payload: {}, occurred_at: "2026-01-01T00:00:00Z", hint_body_md: null }],
  available_hints: [{ id: "hint-1", ordinal: 1 }],
};

describe("AttemptPageContent", () => {
  it("renders attempt workspace", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => attemptDetail,
      })
    );

    render(<AttemptPageContent slug="pair-sum-lookup" attemptId="attempt-1" />);
    expect(await screen.findByText("Pair Sum Lookup")).toBeInTheDocument();
    expect(screen.getByText("Find two numbers.")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("// Paste a solution sketch or code here...")).toBeInTheDocument();
  });

  it("renders quiz options instead of a code editor", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          ...attemptDetail,
          problem: {
            ...attemptDetail.problem,
            activity_kind: "quiz",
            options: [
              { id: "a", label: "Option A" },
              { id: "b", label: "Option B" },
            ],
          },
        }),
      })
    );

    render(<AttemptPageContent slug="sql-inner-join-drop" attemptId="attempt-1" />);
    expect(await screen.findByText("Option A")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("// Paste a solution sketch or code here...")).not.toBeInTheDocument();
    expect(screen.queryByText("Outcome")).not.toBeInTheDocument();
  });

  it("reveals hint via event API", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => attemptDetail,
      });

    vi.stubGlobal("fetch", fetchMock);

    render(<AttemptPageContent slug="pair-sum-lookup" attemptId="attempt-1" />);
    const revealButton = await screen.findByText("Reveal");
    fireEvent.click(revealButton);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/attempts/attempt-1/events",
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
