import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/account",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
  listTargetProfiles: vi.fn(),
  getMyTarget: vi.fn(),
  setMyTarget: vi.fn(),
}));

import AccountPage from "@/app/account/page";
import { getCurrentUser, getMyTarget, listTargetProfiles, setMyTarget } from "@/lib/api";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AccountPage target role", () => {
  it("saves the selected target profile", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({
      status: 200,
      data: {
        id: "u1",
        email: "a@b.com",
        display_name: "Alex",
        created_at: "2026-01-01T00:00:00Z",
      },
    });
    vi.mocked(listTargetProfiles).mockResolvedValue({
      status: 200,
      data: {
        disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
        items: [
          {
            slug: "product-sde",
            name: "Product SDE",
            description: "Baseline",
            disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
          },
        ],
      },
    });
    vi.mocked(getMyTarget).mockResolvedValue({
      status: 200,
      data: { profile: null, selected_at: null, disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements." },
    });
    vi.mocked(setMyTarget).mockResolvedValue({
      status: 200,
      data: {
        selected_at: "2026-08-27T00:00:00Z",
        disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
        profile: {
          slug: "product-sde",
          name: "Product SDE",
          description: "Baseline",
          disclaimer: "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
        },
      },
    });

    render(<AccountPage />);
    await waitFor(() => {
      expect(screen.getByLabelText("Selected target")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText("Selected target"), { target: { value: "product-sde" } });
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));
    await waitFor(() => {
      expect(setMyTarget).toHaveBeenCalledWith("product-sde");
    });
    expect(
      screen.getByText(/not official company hiring requirements/i),
    ).toBeInTheDocument();
  });
});
