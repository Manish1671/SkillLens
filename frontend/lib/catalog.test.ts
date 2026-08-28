import { describe, expect, it, vi } from "vitest";

import { listProblems, listTopics } from "./api";

describe("catalog api client", () => {
  it("lists topics", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [{ slug: "arrays-and-hashing", name: "Arrays & Hashing", sort_order: 10 }],
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await listTopics();
    expect(result.status).toBe(200);
    expect(result.data?.[0]?.slug).toBe("arrays-and-hashing");

    vi.unstubAllGlobals();
  });

  it("lists problems with filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [],
        next_cursor: null,
        has_more: false,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await listProblems({
      topic: "arrays-and-hashing",
      difficulty: "easy",
      q: "pair",
      limit: 5,
    });
    expect(result.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/problems?topic=arrays-and-hashing&difficulty=easy&q=pair&limit=5",
      { credentials: "include" }
    );

    vi.unstubAllGlobals();
  });
});
