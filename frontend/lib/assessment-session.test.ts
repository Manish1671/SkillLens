import { describe, expect, it } from "vitest";

import { clientAttemptId, fingerprintPlan } from "./assessment-session";
import { howDidWeAssessYou } from "./assessment-explain";

describe("assessment session helpers", () => {
  it("builds a stable client_attempt_id within 64 characters", () => {
    const id = clientAttemptId("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", 10, 2);
    expect(id.startsWith("ap-")).toBe(true);
    expect(id.length).toBeLessThanOrEqual(64);
    expect(clientAttemptId("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", 10, 2)).toBe(id);
  });

  it("fingerprints plan items deterministically", () => {
    const items = [
      { position: 1, problem_slug: "a" },
      { position: 2, problem_slug: "b" },
    ];
    expect(fingerprintPlan(items as never)).toBe("1:a|2:b");
  });
});

describe("assessment explanations", () => {
  it("uses the selected target name instead of a hard-coded role", () => {
    const sentences = howDidWeAssessYou({
      targetName: "Intern SWE",
      dsaAssessed: 7,
      csAssessed: 4,
      planDsaCount: 7,
      planCsCount: 4,
    });
    expect(sentences.join(" ")).toContain("Intern SWE");
    expect(sentences.join(" ")).not.toContain("Product SDE");
    expect(sentences).toHaveLength(3);
  });
});
