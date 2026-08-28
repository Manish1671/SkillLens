import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
}));

import { HomePageContent } from "./HomePageContent";
import { getCurrentUser } from "@/lib/api";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("HomePageContent", () => {
  it("renders the marketing landing page when unauthenticated", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      status: 401,
      error: { detail: "Authentication required", code: "unauthorized" },
    });
    render(<HomePageContent />);
    await waitFor(() => {
      expect(screen.getByText("Know what you actually understand.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Placement readiness")).not.toBeInTheDocument();
  });
});
