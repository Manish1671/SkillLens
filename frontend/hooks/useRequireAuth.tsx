"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getCurrentUser, type PublicUser } from "@/lib/api";
import { loginHref } from "@/lib/safe-next";
import { LoadingState } from "@/components/ui/StatePanels";

export function useRequireAuth(nextPath: string): {
  user: PublicUser | null;
  ready: boolean;
} {
  const router = useRouter();
  const [user, setUser] = useState<PublicUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCurrentUser()
      .then((result) => {
        if (cancelled) return;
        if (!result.data) {
          router.replace(loginHref(nextPath));
          return;
        }
        setUser(result.data);
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        router.replace(loginHref(nextPath));
      });
    return () => {
      cancelled = true;
    };
  }, [nextPath, router]);

  return { user, ready };
}

export function AuthGate({
  nextPath,
  children,
}: {
  nextPath: string;
  children: (user: PublicUser) => React.ReactNode;
}) {
  const { user, ready } = useRequireAuth(nextPath);
  if (!ready || !user) {
    return <LoadingState message="Checking session..." />;
  }
  return <>{children(user)}</>;
}
