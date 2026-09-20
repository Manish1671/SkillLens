"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Button, ButtonLink } from "@/components/ui/Button";
import { IconMenu } from "@/components/ui/Icons";
import { getCurrentUser, getMyTarget, logoutUser, type PublicUser } from "@/lib/api";
import { loginHref } from "@/lib/safe-next";

const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/skills", label: "Skills" },
  { href: "/problems", label: "Practice" },
  { href: "/assessment", label: "Assess" },
];

function UserAvatar({ name }: { name: string }) {
  return (
    <span
      className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-white"
      aria-hidden
    >
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

export function AppShell({
  children,
  fullWidth = false,
}: {
  children: React.ReactNode;
  fullWidth?: boolean;
}) {
  const pathname = usePathname();
  const [user, setUser] = useState<PublicUser | null | undefined>(undefined);
  const [targetName, setTargetName] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(async (result) => {
        const nextUser = result.data ?? null;
        setUser(nextUser);
        if (!nextUser) {
          setTargetName(null);
          return;
        }
        if (typeof getMyTarget !== "function") return;
        const target = await getMyTarget();
        setTargetName(target.data?.profile?.name ?? null);
      })
      .catch(() => {
        setUser(null);
        setTargetName(null);
      });
  }, []);

  async function handleLogout() {
    await logoutUser();
    setUser(null);
    setTargetName(null);
    window.location.href = "/";
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    if (href === "/problems") {
      return pathname.startsWith("/problems") || pathname.startsWith("/core-cs");
    }
    return pathname.startsWith(href);
  }

  return (
    <div className="min-h-screen bg-background text-ink">
      <header className="sticky top-0 z-50 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="sl-container">
          <div className="grid h-12 grid-cols-[auto_1fr_auto] items-center gap-3 md:grid-cols-[1fr_auto_1fr]">
            <div className="justify-self-start">
              <Logo />
            </div>

            <nav className="hidden items-center justify-center gap-0.5 md:flex" aria-label="Main">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative px-3 py-2 text-[13px] font-medium transition-colors ${
                    isActive(link.href) ? "text-ink" : "text-muted hover:text-ink"
                  }`}
                >
                  {link.label}
                  {isActive(link.href) ? (
                    <span className="absolute inset-x-3 -bottom-[9px] h-px bg-accent" />
                  ) : null}
                </Link>
              ))}
            </nav>

            <div className="hidden items-center justify-self-end gap-2 md:flex">
              {user === undefined ? (
                <span className="h-7 w-24 animate-pulse rounded bg-surface-muted" />
              ) : user ? (
                <>
                  <Link
                    href="/account"
                    className="max-w-[140px] truncate px-1.5 py-1 text-[12px] text-muted hover:text-ink"
                    title="Target profile"
                  >
                    {targetName ?? "Set target"}
                  </Link>
                  <Link
                    href="/account"
                    className="flex items-center gap-2 rounded-md px-1.5 py-1 text-[13px] text-muted hover:text-ink"
                  >
                    <UserAvatar name={user.display_name} />
                    <span className="max-w-[110px] truncate">{user.display_name}</span>
                  </Link>
                  <Button variant="ghost" size="sm" onClick={() => handleLogout()}>
                    Log out
                  </Button>
                </>
              ) : (
                <>
                  <ButtonLink href={loginHref(pathname || "/")} variant="ghost" size="sm">
                    Log in
                  </ButtonLink>
                  <ButtonLink href="/register" size="sm">
                    Register
                  </ButtonLink>
                </>
              )}
            </div>

            <button
              type="button"
              className="justify-self-end rounded-md p-2 text-muted hover:bg-surface-muted md:hidden"
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((v) => !v)}
            >
              <IconMenu />
            </button>
          </div>

          {mobileOpen ? (
            <nav className="border-t border-border py-3 md:hidden" aria-label="Mobile">
              <div className="flex flex-col gap-1">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className={`rounded-md px-3 py-2 text-sm ${
                      isActive(link.href) ? "bg-accent-soft text-accent" : "text-muted"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                <Link
                  href="/core-cs"
                  onClick={() => setMobileOpen(false)}
                  className={`rounded-md px-3 py-2 text-sm ${
                    pathname.startsWith("/core-cs") ? "bg-accent-soft text-accent" : "text-muted"
                  }`}
                >
                  Core CS
                </Link>
                <div className="mt-2 flex flex-col gap-2 border-t border-border pt-3">
                  {user ? (
                    <>
                      <Link href="/account" className="px-3 py-2 text-sm" onClick={() => setMobileOpen(false)}>
                        {targetName ? `Target: ${targetName}` : "Account"}
                      </Link>
                      <button type="button" className="px-3 py-2 text-left text-sm text-muted" onClick={() => handleLogout()}>
                        Log out
                      </button>
                    </>
                  ) : (
                    <>
                      <ButtonLink href={loginHref(pathname || "/")} variant="secondary" size="sm" className="mx-3">
                        Log in
                      </ButtonLink>
                      <ButtonLink href="/register" size="sm" className="mx-3">
                        Register
                      </ButtonLink>
                    </>
                  )}
                </div>
              </div>
            </nav>
          ) : null}
        </div>
      </header>

      <main className={fullWidth ? "" : "sl-container py-5 sm:py-6"}>{children}</main>
    </div>
  );
}
