"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState, Suspense } from "react";

import { AppShell } from "@/components/ui/AppShell";
import { Button } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/Primitives";
import { ErrorState, LoadingState, PageHeader } from "@/components/ui/StatePanels";
import {
  getCurrentUser,
  getMyTarget,
  listTargetProfiles,
  logoutUser,
  setMyTarget,
  type PublicUser,
  type TargetProfileSummary,
} from "@/lib/api";

function AccountPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const assessmentNotice = searchParams.get("reason") === "assessment";
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<TargetProfileSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string>("");
  const [disclaimer, setDisclaimer] = useState(
    "SkillLens target profiles are internal readiness models, not official company hiring requirements.",
  );
  const [savingTarget, setSavingTarget] = useState(false);
  const [targetError, setTargetError] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await getCurrentUser();
    if (result.error) {
      setError(result.error.detail);
      setUser(null);
      if (result.status === 401) {
        router.push("/login");
      }
      setLoading(false);
      return;
    }
    setUser(result.data ?? null);
    const [profileList, target] = await Promise.all([listTargetProfiles(), getMyTarget()]);
    if (profileList.data) {
      setProfiles(profileList.data.items);
      setDisclaimer(profileList.data.disclaimer);
    }
    if (target.data?.profile) {
      setSelectedSlug(target.data.profile.slug);
    }
    setLoading(false);
  }, [router]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  async function handleLogout() {
    await logoutUser();
    router.push("/");
  }

  async function handleSaveTarget() {
    if (!selectedSlug) {
      return;
    }
    setSavingTarget(true);
    setTargetError(null);
    const result = await setMyTarget(selectedSlug);
    if (result.error) {
      setTargetError(result.error.detail);
    }
    setSavingTarget(false);
    if (assessmentNotice) {
      router.push("/assessment");
    }
  }

  return (
    <AppShell>
      <div className="max-w-3xl space-y-6">
        <PageHeader title="Account" description="Your target, profile, and session." />

        {loading ? <LoadingState message="Loading account..." /> : null}

        {user ? (
          <div className="grid gap-8 sm:grid-cols-2">
            <section>
              <SectionLabel>Profile</SectionLabel>
              <dl className="mt-3 space-y-4 text-sm">
                <div>
                  <dt className="text-muted">Display name</dt>
                  <dd className="mt-0.5 font-medium">{user.display_name}</dd>
                </div>
                <div>
                  <dt className="text-muted">Email</dt>
                  <dd className="mt-0.5 font-medium">{user.email}</dd>
                </div>
              </dl>
            </section>
            <section>
              <SectionLabel>Authentication</SectionLabel>
              <p className="mt-3 text-sm text-muted">
                Session managed via secure httpOnly cookies.
              </p>
              <p className="mt-2 text-xs text-muted">Created {new Date(user.created_at).toLocaleDateString()}</p>
              <Button variant="secondary" className="mt-4" onClick={() => handleLogout()}>
                Log out
              </Button>
            </section>
            <section className="sm:col-span-2">
              <SectionLabel>Target role</SectionLabel>
              {assessmentNotice ? (
                <p className="mt-3 text-sm text-ink" role="status">
                  Choose a target before assessing readiness.
                </p>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  SkillLens compares your preparation against this readiness model.
                </p>
              )}
              <label className="mt-4 block text-sm font-medium" htmlFor="target-profile">
                Selected target
              </label>
              <select
                id="target-profile"
                className="mt-1 w-full max-w-md rounded-md border border-border bg-surface px-3 py-2 text-sm"
                value={selectedSlug}
                onChange={(event) => setSelectedSlug(event.target.value)}
              >
                <option value="">Choose a target profile</option>
                {profiles.map((profile) => (
                  <option key={profile.slug} value={profile.slug}>
                    {profile.name}
                  </option>
                ))}
              </select>
              <p className="mt-3 max-w-2xl text-xs text-muted">{disclaimer}</p>
              <Button
                className="mt-4"
                disabled={!selectedSlug || savingTarget}
                onClick={() => handleSaveTarget()}
              >
                {savingTarget ? "Saving..." : "Save target"}
              </Button>
              {targetError ? <p className="mt-2 text-sm text-danger">{targetError}</p> : null}
            </section>
          </div>
        ) : null}

        {error && !loading ? <ErrorState message={error} onRetry={loadUser} /> : null}

        {!loading && !user && !error ? (
          <p className="text-sm text-muted">
            <Link href="/login" className="font-medium text-accent hover:underline">
              Log in
            </Link>{" "}
            to view your account.
          </p>
        ) : null}
      </div>
    </AppShell>
  );
}

export default function AccountPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading account..." />}>
      <AccountPageContent />
    </Suspense>
  );
}
