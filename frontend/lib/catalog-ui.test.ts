import { describe, expect, it } from "vitest";

import { mergeSkillProfile } from "./catalog-ui";

describe("mergeSkillProfile", () => {
  it("does not invent mastery scores for catalog skills", () => {
    const merged = mergeSkillProfile(
      [
        {
          slug: "arrays",
          name: "Arrays",
          description: "",
          topic_slug: null,
          is_foundational: true,
          sort_order: 10,
          prerequisite_skill_ids: [],
        },
      ],
      []
    );
    expect(merged[0]?.score).toBeNull();
    expect(merged[0]?.status).toBe("insufficient");
    expect(merged[0]?.evidence_count).toBe(0);
  });
});
