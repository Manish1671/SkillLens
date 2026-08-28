import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mockPush = vi.fn();
const search = new URLSearchParams("next=/skills");

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => search,
  usePathname: () => "/login",
}));

vi.mock("@/lib/api", () => ({
  loginUser: vi.fn(),
  getCurrentUser: vi.fn().mockResolvedValue({ status: 401 }),
  logoutUser: vi.fn(),
  getMyTarget: vi.fn().mockResolvedValue({ status: 401 }),
}));

import LoginPage from "@/app/login/page";
import { loginUser } from "@/lib/api";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LoginPage next redirect", () => {
  it("returns to the safe next path after login", async () => {
    vi.mocked(loginUser).mockResolvedValue({
      status: 200,
      data: {
        id: "u1",
        email: "a@b.com",
        display_name: "Manish",
        created_at: "2026-01-01T00:00:00Z",
      },
    });

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/skills");
    });
  });
});
