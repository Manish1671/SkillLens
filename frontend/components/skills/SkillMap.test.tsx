import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SkillMap } from "./SkillMap";

afterEach(() => cleanup());

describe("SkillMap", () => {
  it("renders assessed and evidence-needed nodes from the real graph", () => {
    render(
      <SkillMap
        nodes={[
          { slug: "arrays", name: "Arrays", score: "0.87", status: "assessed", confidence: "0.8" },
          { slug: "sliding-window", name: "Sliding Window", score: null, status: "insufficient" },
        ]}
        edges={[{ from: "arrays", to: "sliding-window" }]}
        focusSlug="sliding-window"
      />
    );

    expect(screen.getByTestId("skill-map")).toBeInTheDocument();
    expect(screen.getByLabelText("Skill dependency map")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("Evidence needed")).toBeInTheDocument();
  });
});
