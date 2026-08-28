"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { AppShell } from "@/components/ui/AppShell";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/StatePanels";
import { loginUser } from "@/lib/api";
import { safeInternalPath } from "@/lib/safe-next";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const result = await loginUser({ email, password });
    setSubmitting(false);
    if (result.error) {
      setError(result.error.detail);
      return;
    }

    router.push(safeInternalPath(searchParams.get("next")));
  }

  return (
    <div className="grid gap-10 lg:grid-cols-12 lg:items-center">
      <div className="hidden lg:col-span-5 lg:block">
        <Logo />
        <h1 className="mt-8 text-3xl font-semibold tracking-tight">Return to your skill model.</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Evidence, mastery, and the next problem are waiting where you left them.
        </p>
      </div>
      <div className="lg:col-span-6 lg:col-start-7">
        <h1 className="text-2xl font-semibold lg:hidden">Log in</h1>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
          <label className="block space-y-1.5 text-sm">
            <span id="login-email-label">Email</span>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              aria-labelledby="login-email-label"
              aria-invalid={Boolean(error)}
              className="sl-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-1.5 text-sm">
            <span id="login-password-label">Password</span>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              aria-labelledby="login-password-label"
              className="sl-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error ? (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logging in..." : "Log in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-muted">
          Need an account?{" "}
          <Link href="/register" className="font-medium text-accent hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AppShell>
      <Suspense fallback={<LoadingState message="Loading..." />}>
        <LoginForm />
      </Suspense>
    </AppShell>
  );
}
