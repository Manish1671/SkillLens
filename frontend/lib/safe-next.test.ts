import { describe, expect, it } from "vitest";

import { loginHref, safeInternalPath } from "./safe-next";

describe("safeInternalPath", () => {
  it("allows in-app paths", () => {
    expect(safeInternalPath("/skills")).toBe("/skills");
    expect(safeInternalPath("/skills/sliding-window")).toBe("/skills/sliding-window");
  });

  it("rejects open redirects", () => {
    expect(safeInternalPath("https://evil.example")).toBe("/");
    expect(safeInternalPath("//evil.example")).toBe("/");
    expect(safeInternalPath("/\\evil")).toBe("/");
    expect(safeInternalPath(null)).toBe("/");
  });

  it("builds a login href with next", () => {
    expect(loginHref("/skills")).toBe("/login?next=%2Fskills");
  });
});
