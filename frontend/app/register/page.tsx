"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { AppShell } from "@/components/ui/AppShell";
import { Button } from "@/components/ui/Button";
import { registerUser } from "@/lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setSubmitting(true);

    const result = await registerUser({
      email,
      password,
      display_name: displayName,
    });
    setSubmitting(false);

    if (result.error) {
      setError(result.error.detail);
      return;
    }

    setSuccess(true);
  }

  return (
    <AppShell>
      <div className="grid gap-10 lg:grid-cols-12 lg:items-center">
        <div className="hidden lg:col-span-5 lg:block">
          <Logo />
          <h1 className="mt-8 text-3xl font-semibold tracking-tight">Start your skill model.</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            One account. Evidence from every attempt. Recommendations you can inspect.
          </p>
        </div>
        <div className="lg:col-span-6 lg:col-start-7">
          <h1 className="text-2xl font-semibold lg:hidden">Create account</h1>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block space-y-1.5 text-sm">
              <span>Display name</span>
              <input
                className="sl-input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </label>
            <label className="block space-y-1.5 text-sm">
              <span>Email</span>
              <input
                type="email"
                autoComplete="email"
                className="sl-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label className="block space-y-1.5 text-sm">
              <span>Password (8+ characters)</span>
              <input
                type="password"
                autoComplete="new-password"
                className="sl-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </label>
            {error ? (
              <p className="text-sm text-danger" role="alert">
                {error}
              </p>
            ) : null}
            {success ? (
              <p className="text-sm text-success" role="status">
                Account created. You can{" "}
                <Link href="/login" className="font-medium underline">
                  log in
                </Link>{" "}
                now.
              </p>
            ) : null}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Creating account..." : "Register"}
            </Button>
          </form>
          <p className="mt-4 text-sm text-muted">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-accent hover:underline">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </AppShell>
  );
}
