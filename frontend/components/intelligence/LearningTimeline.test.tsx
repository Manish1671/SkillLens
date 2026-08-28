import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { LearningTimeline } from "./LearningTimeline";

afterEach(() => cleanup());

describe("LearningTimeline", () => {
  it("shows an intentional empty state", () => {
    render(<LearningTimeline attempts={[]} />);
    expect(screen.getByTestId("learning-timeline")).toHaveTextContent(
      "Complete your first problem to create your first evidence point."
    );
  });

  it("renders submitted attempts as evidence", () => {
    render(
      <LearningTimeline
        attempts={[
          {
            id: "1",
            problem: {
              id: "p",
              slug: "pair-sum-lookup",
              title: "Pair Sum",
              difficulty: "easy",
            },
            status: "submitted",
            started_at: "2026-08-26T00:00:00Z",
            submitted_at: "2026-08-26T00:10:00Z",
            time_spent_seconds: 600,
            hints_used_count: 0,
            is_correct: true,
            mistake_type: null,
          },
        ]}
      />
    );
    expect(screen.getByText("Solved Pair Sum")).toBeInTheDocument();
    expect(screen.getByText("DSA signal")).toBeInTheDocument();
  });

  it("renders quiz attempts as Core CS evidence", () => {
    render(
      <LearningTimeline
        attempts={[
          {
            id: "2",
            problem: {
              id: "q",
              slug: "sql-joins-inner",
              title: "SQL Joins",
              difficulty: "easy",
              activity_kind: "quiz",
            },
            status: "submitted",
            started_at: "2026-08-26T00:00:00Z",
            submitted_at: "2026-08-26T00:10:00Z",
            time_spent_seconds: 120,
            hints_used_count: 0,
            is_correct: true,
            mistake_type: null,
          },
        ]}
      />
    );
    expect(screen.getByText("Quiz completed · SQL Joins")).toBeInTheDocument();
    expect(screen.getByText("Core CS signal")).toBeInTheDocument();
  });
});
