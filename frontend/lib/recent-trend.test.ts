import { describe, expect, it } from "vitest";

import { recentTrendFromSnapshots } from "./recent-trend";

describe("recentTrendFromSnapshots", () => {
  it("returns none without enough history", () => {
    expect(recentTrendFromSnapshots([]).kind).toBe("none");
    expect(recentTrendFromSnapshots([{ score: "0.5", computed_at: "2026-01-01" }]).kind).toBe("none");
  });

  it("labels a presentation-level recent decline from adjacent snapshots", () => {
    const trend = recentTrendFromSnapshots([
      { score: "0.72", computed_at: "2026-01-01T00:00:00Z" },
      { score: "0.51", computed_at: "2026-01-08T00:00:00Z" },
    ]);
    expect(trend.kind).toBe("decline");
    expect(trend.label).toBe("Recent decline");
    expect(trend.from).toBeCloseTo(0.72);
    expect(trend.to).toBeCloseTo(0.51);
  });

  it("labels improvement and stable honestly", () => {
    expect(
      recentTrendFromSnapshots([
        { score: "0.40", computed_at: "2026-01-01T00:00:00Z" },
        { score: "0.55", computed_at: "2026-01-08T00:00:00Z" },
      ]).kind
    ).toBe("rise");
    expect(
      recentTrendFromSnapshots([
        { score: "0.50", computed_at: "2026-01-01T00:00:00Z" },
        { score: "0.52", computed_at: "2026-01-08T00:00:00Z" },
      ]).kind
    ).toBe("stable");
  });
});
