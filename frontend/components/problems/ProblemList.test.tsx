import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProblemListItem } from "@/lib/api";

import {
  ProblemFilters,
  ProblemListSection,
  type ProblemFilterValues,
} from "./ProblemList";

afterEach(() => {
  cleanup();
});

const sampleProblem: ProblemListItem = {
  id: "1",
  slug: "pair-sum-lookup",
  title: "Pair Sum Lookup",
  difficulty: "easy",
  estimated_minutes: 20,
  topic: { slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 },
  skills: [
    { slug: "hashing", name: "Hashing", weight: "1.0", is_primary: true },
  ],
  learner_state: null,
};

describe("ProblemList UI", () => {
  it("renders problem list", () => {
    render(
      <ProblemListSection
        loading={false}
        error={null}
        problems={[sampleProblem]}
        emptyMessage="No problems"
      />
    );

    expect(screen.getByText("Pair Sum Lookup")).toBeInTheDocument();
    expect(screen.getByText("Hashing")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(
      <ProblemListSection
        loading={false}
        error={null}
        problems={[]}
        emptyMessage="No problems match your filters."
      />
    );

    expect(screen.getByText("No problems match your filters.")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(
      <ProblemListSection
        loading={true}
        error={null}
        problems={[]}
        emptyMessage="No problems"
      />
    );

    expect(screen.getByText("Loading problems...")).toBeInTheDocument();
  });

  it("shows API error state", () => {
    render(
      <ProblemListSection
        loading={false}
        error="Server error"
        problems={[]}
        emptyMessage="No problems"
      />
    );

    expect(screen.getByText("Server error")).toBeInTheDocument();
  });

  it("handles filter interaction", () => {
    const onChange = vi.fn();
    const values: ProblemFilterValues = {
      q: "",
      topic: "",
      skill: "",
      difficulty: "",
      activity: "coding",
    };

    render(
      <ProblemFilters
        topics={[{ slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 }]}
        skills={[
          {
            slug: "hashing",
            name: "Hashing",
            description: "",
            topic_slug: "arrays-and-hashing",
            is_foundational: false,
            sort_order: 20,
            prerequisite_skill_ids: [],
          },
        ]}
        values={values}
        onChange={onChange}
      />
    );

    fireEvent.change(screen.getByPlaceholderText("Search problems..."), {
      target: { value: "pair" },
    });
    expect(onChange).toHaveBeenCalledWith({ ...values, q: "pair" });
  });

  it("filters by activity kind", () => {
    const onChange = vi.fn();
    const values: ProblemFilterValues = {
      q: "",
      topic: "",
      skill: "",
      difficulty: "",
      activity: "coding",
    };

    render(
      <ProblemFilters
        topics={[{ slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 }]}
        skills={[]}
        values={values}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Quiz" }));
    expect(onChange).toHaveBeenCalledWith({ ...values, activity: "quiz" });
  });
});
