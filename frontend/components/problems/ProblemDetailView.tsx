"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, ButtonLink } from "@/components/ui/Button";
import { IconArrowRight } from "@/components/ui/Icons";
import { SectionLabel } from "@/components/ui/Primitives";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { getProblem, startAttempt, type ProblemDetail } from "@/lib/api";
import { formatMinutes } from "@/lib/catalog-ui";

import { DifficultyBadge, SkillBadges } from "./ProblemBadges";

export function ProblemDetailView({ slug }: { slug: string }) {
  const router = useRouter();
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const result = await getProblem(slug);
      if (result.error) {
        setError(result.error.detail);
        setProblem(null);
        setLoading(false);
        return;
      }
      setProblem(result.data ?? null);
      setLoading(false);
    }

    load();
  }, [slug]);

  async function handleStart() {
    if (!problem) {
      return;
    }
    setStarting(true);
    setError(null);
    const clientAttemptId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `client-${Date.now()}`;
    const result = await startAttempt({
      problem_id: problem.id,
      client_attempt_id: clientAttemptId,
    });
    if (result.error) {
      setError(result.error.detail);
      setStarting(false);
      if (result.status === 401) {
        router.push("/login");
      }
      return;
    }
    if (result.data) {
      router.push(`/problems/${slug}/attempt/${result.data.id}`);
    }
  }

  if (loading) {
    return <LoadingState message="Loading problem..." />;
  }

  if (error && !problem) {
    return <ErrorState message={error} />;
  }

  if (!problem) {
    return <ErrorState message="Problem not found." />;
  }

  const primarySkill = problem.skills.find((s) => s.is_primary);

  return (
    <article className="space-y-5">
      <nav className="text-sm text-muted">
        <Link href="/problems" className="hover:text-accent">Problems</Link>
        <span className="mx-2">/</span>
        <span className="text-ink">{problem.title}</span>
      </nav>

      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{problem.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted">
            <DifficultyBadge difficulty={problem.difficulty} />
            <span>{formatMinutes(problem.estimated_minutes)}</span>
            {problem.activity_kind === "quiz" ? (
              <span className="text-xs font-semibold uppercase tracking-wide text-muted">Quiz</span>
            ) : null}
            {problem.learner_state?.solved ? (
              <span className="font-medium text-success">Solved</span>
            ) : null}
            {problem.learner_state?.in_progress ? (
              <span className="font-medium text-warning">In progress</span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-12">
        <section className="lg:col-span-8">
          <SectionLabel>{problem.activity_kind === "quiz" ? "Question" : "Problem statement"}</SectionLabel>
          <div className="mt-4 whitespace-pre-wrap text-[15px] leading-7 text-ink">{problem.prompt_md}</div>
        </section>

        <aside className="lg:col-span-4 lg:sticky lg:top-16 h-fit">
          <SectionLabel>Problem intelligence</SectionLabel>
          <dl className="mt-4 space-y-4 border-t border-border pt-4 text-sm">
              <div>
                <dt className="sl-label">Target skill</dt>
                <dd className="mt-1 font-medium">{primarySkill?.name ?? "—"}</dd>
              </div>
              <div>
                <dt className="sl-label">Supporting skills</dt>
                <dd className="mt-1">
                  <SkillBadges skills={problem.skills.filter((s) => !s.is_primary)} />
                </dd>
              </div>
              <div>
                <dt className="sl-label">Estimated</dt>
                <dd className="mt-1 font-medium">{formatMinutes(problem.estimated_minutes)}</dd>
              </div>
              <div>
                <dt className="sl-label">Hints available</dt>
                <dd className="mt-1 font-medium">{problem.hint_count}</dd>
              </div>
            </dl>

            {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

            <div className="mt-6 space-y-2">
              <Button className="w-full" disabled={starting} onClick={() => handleStart()}>
                {starting
                  ? "Starting..."
                  : problem.learner_state?.in_progress
                    ? "Resume attempt"
                    : problem.activity_kind === "quiz"
                      ? "Start quiz"
                      : "Start solving"}
                {!starting ? <IconArrowRight /> : null}
              </Button>
              <ButtonLink href="/problems" variant="ghost" className="w-full">
                Back to practice
              </ButtonLink>
            </div>
        </aside>
      </div>
    </article>
  );
}
