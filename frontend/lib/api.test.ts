import { describe, expect, it, vi } from "vitest";

import { getCurrentUser, loginUser, logoutUser, registerUser } from "./api";

describe("auth api client", () => {
  it("performs register → login → me → logout flow", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: "user-1",
          email: "flow@example.com",
          display_name: "Flow User",
          created_at: "2026-01-01T00:00:00Z",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          id: "user-1",
          email: "flow@example.com",
          display_name: "Flow User",
          created_at: "2026-01-01T00:00:00Z",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          id: "user-1",
          email: "flow@example.com",
          display_name: "Flow User",
          created_at: "2026-01-01T00:00:00Z",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Authentication required", code: "unauthorized" }),
      });

    vi.stubGlobal("fetch", fetchMock);

    const register = await registerUser({
      email: "flow@example.com",
      password: "password123",
      display_name: "Flow User",
    });
    expect(register.status).toBe(201);

    const login = await loginUser({ email: "flow@example.com", password: "password123" });
    expect(login.status).toBe(200);

    const me = await getCurrentUser();
    expect(me.status).toBe(200);
    expect(me.data?.email).toBe("flow@example.com");

    const logout = await logoutUser();
    expect(logout.status).toBe(200);

    const meAfterLogout = await getCurrentUser();
    expect(meAfterLogout.status).toBe(401);

    vi.unstubAllGlobals();
  });

  it("does not hang when /api/auth/me returns HTML or the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("Failed to fetch")));
    const network = await getCurrentUser();
    expect(network.status).toBe(0);
    expect(network.error?.code).toBe("network_error");
    vi.unstubAllGlobals();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error("not json");
        },
      }),
    );
    const html = await getCurrentUser();
    expect(html.status).toBe(502);
    expect(html.data).toBeUndefined();
    vi.unstubAllGlobals();
  });
});
