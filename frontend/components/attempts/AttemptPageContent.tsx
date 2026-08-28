"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AttemptResultPanel } from "@/components/attempts/AttemptResultPanel";
import { QuizOptionFields } from "@/components/attempts/QuizOptionFields";
import { DifficultyBadge } from "@/components/problems/ProblemBadges";
import { Button } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/Primitives";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import {
  abandonAttempt,
  getAttempt,
  getMyReadiness,
  getNextPlacementAction,
  recordAttemptEvent,
  submitAttempt,
  type AttemptDetail,
  type MistakeType,
  type PlacementReadiness,
  type PlacementActionItem,
  type SubmitAssessmentOutcome,
} from "@/lib/api";

const MISTAKE_OPTIONS: { value: MistakeType; label: string }[] = [
  { value: "off_by_one", label: "Off by one" },
  { value: "wrong_data_structure", label: "Wrong data structure" },
  { value: "missed_edge_case", label: "Missed edge case" },
  { value: "incorrect_complexity", label: "Incorrect complexity" },
  { value: "logic_error", label: "Logic error" },
  { value: "unknown", label: "Unknown" },
];

function formatElapsed(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function AttemptPageContent({
  slug,
  attemptId,
}: {
  slug: string;
  attemptId: string;
}) {
  const router = useRouter();
  const [detail, setDetail] = useState<AttemptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [codeText, setCodeText] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isCorrect, setIsCorrect] = useState(true);
  const [mistakeType, setMistakeType] = useState<MistakeType>("logic_error");
  const [actionError, setActionError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [revealingHintId, setRevealingHintId] = useState<string | null>(null);
  const [submitAssessment, setSubmitAssessment] = useState<SubmitAssessmentOutcome | null>(null);
  const [readiness, setReadiness] = useState<PlacementReadiness | null>(null);
  const [nextAction, setNextAction] = useState<PlacementActionItem | null>(null);
  const [actionState, setActionState] = useState<string | undefined>();
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const result = await getAttempt(attemptId);
      if (result.error) {
        setError(result.error.detail);
        setDetail(null);
        setLoading(false);
        if (result.status === 401) {
          router.push("/login");
        }
        return;
      }
      setDetail(result.data ?? null);
      setLoading(false);
    }

    load();
  }, [attemptId, router]);

  useEffect(() => {
    if (!detail || detail.attempt.status !== "in_progress") {
      return;
    }
    const interval = window.setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(interval);
  }, [detail]);

  const revealedHintMap = useMemo(() => {
    const map: Record<string, string> = {};
    if (!detail) {
      return map;
    }
    for (const event of detail.events) {
      if (event.event_type === "hint_revealed" && event.hint_body_md) {
        const hintId = event.payload.hint_id as string | undefined;
        if (hintId) {
          map[hintId] = event.hint_body_md;
        }
      }
    }
    return map;
  }, [detail]);

  const revealedHintIds = new Set(Object.keys(revealedHintMap));

  async function handleRevealHint(hintId: string) {
    setActionError(null);
    setRevealingHintId(hintId);
    const result = await recordAttemptEvent(attemptId, {
      event_type: "hint_revealed",
      payload: { hint_id: hintId },
    });
    setRevealingHintId(null);
    if (result.error) {
      setActionError(result.error.detail);
      return;
    }
    const refresh = await getAttempt(attemptId);
    if (refresh.data) {
      setDetail(refresh.data);
    }
  }

  async function handleSubmit() {
    setActionError(null);
    const isQuiz = detail?.problem.activity_kind === "quiz";
    if (isQuiz && !selectedOption) {
      setActionError("Select an answer before submitting.");
      return;
    }
    setSubmitting(true);
    const result = await submitAttempt(
      attemptId,
      isQuiz
        ? {
            selected_option: selectedOption ?? undefined,
            time_spent_seconds: elapsedSeconds,
          }
        : {
            is_correct: isCorrect,
            time_spent_seconds: elapsedSeconds,
            mistake_type: isCorrect ? undefined : mistakeType,
            code_text: codeText.trim() || undefined,
          }
    );
    setSubmitting(false);
    if (result.error) {
      setActionError(result.error.detail);
      return;
    }
    if (result.data?.assessment) {
      setSubmitAssessment(result.data.assessment);
    }
    const [refresh, readinessResult, actionResult] = await Promise.all([
      getAttempt(attemptId),
      getMyReadiness(),
      getNextPlacementAction({ refresh: true }),
    ]);
    if (refresh.data) {
      setDetail(refresh.data);
    }
    if (readinessResult.data) {
      setReadiness(readinessResult.data);
    }
    setNextAction(actionResult.data?.action ?? null);
    setActionState(actionResult.data?.state);
    setActionMessage(actionResult.data?.message ?? null);
  }

  async function handleAbandon() {
    setActionError(null);
    const result = await abandonAttempt(attemptId);
    if (result.error) {
      setActionError(result.error.detail);
      return;
    }
    const refresh = await getAttempt(attemptId);
    if (refresh.data) {
      setDetail(refresh.data);
    }
  }

  if (loading) {
    return <LoadingState message="Loading attempt workspace..." />;
  }

  if (error || !detail) {
    return (
      <ErrorState
        message={error ?? "Attempt not found or you do not have access."}
        onRetry={() => window.location.reload()}
      />
    );
  }

  const { attempt, problem, available_hints } = detail;
  const isTerminal = attempt.status === "submitted" || attempt.status === "abandoned";
  const isQuiz = (problem.activity_kind ?? "coding") === "quiz";
  const quizOptions = problem.options ?? [];

  return (
    <article className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div>
          <nav className="text-sm text-muted">
            <Link href={`/problems/${slug}`} className="hover:text-accent">{problem.title}</Link>
          </nav>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <DifficultyBadge difficulty={problem.difficulty} />
            {isQuiz ? (
              <span className="text-xs uppercase tracking-wide text-muted">Quiz</span>
            ) : (
              <span className="font-mono text-sm sl-num">{formatElapsed(elapsedSeconds)}</span>
            )}
            <span className="text-xs uppercase tracking-wide text-muted">
              {attempt.status.replace("_", " ")}
            </span>
          </div>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-12">
        <div className="space-y-5 lg:col-span-8">
          <section>
            <SectionLabel>{isQuiz ? "Question" : "Problem statement"}</SectionLabel>
            <div className="mt-3 whitespace-pre-wrap text-[15px] leading-7">{problem.prompt_md}</div>
          </section>

          {!isTerminal ? (
            <section className="space-y-4">
              {isQuiz ? (
                <QuizOptionFields
                  options={quizOptions}
                  selectedOption={selectedOption}
                  onSelect={setSelectedOption}
                />
              ) : (
                <>
                  <SectionLabel>Your work</SectionLabel>
                  <label className="block space-y-2 text-sm">
                    <span className="text-muted">Code (optional)</span>
                    <textarea
                      className="sl-code-panel w-full min-h-[200px] p-4 focus:outline-none focus:ring-2 focus:ring-accent/40"
                      value={codeText}
                      onChange={(event) => setCodeText(event.target.value)}
                      placeholder="// Paste a solution sketch or code here..."
                      spellCheck={false}
                    />
                  </label>

                  <fieldset className="space-y-2 text-sm">
                    <legend className="sl-label">Outcome</legend>
                    <label className="flex items-center gap-2">
                      <input type="radio" checked={isCorrect} onChange={() => setIsCorrect(true)} />
                      Correct
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="radio" checked={!isCorrect} onChange={() => setIsCorrect(false)} />
                      Incorrect
                    </label>
                  </fieldset>

                  {!isCorrect ? (
                    <label className="block space-y-1 text-sm">
                      <span className="text-muted">Mistake type</span>
                      <select
                        className="sl-input"
                        value={mistakeType}
                        onChange={(event) => setMistakeType(event.target.value as MistakeType)}
                      >
                        {MISTAKE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </>
              )}

              {actionError ? <p className="text-sm text-danger">{actionError}</p> : null}

              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={submitting || attempt.status === "submitted"}
                  onClick={() => handleSubmit()}
                  size="lg"
                >
                  {submitting ? "Submitting..." : isQuiz ? "Submit answer" : "Submit attempt"}
                </Button>
                <Button variant="ghost" onClick={() => handleAbandon()}>
                  Abandon
                </Button>
              </div>
            </section>
          ) : null}
        </div>

        <aside className="space-y-5 lg:col-span-4 lg:sticky lg:top-16 h-fit">
          <section className="border border-border bg-surface p-4">
            <SectionLabel>Hints</SectionLabel>
            {available_hints.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No hints for this problem.</p>
            ) : (
              <div className="mt-3 space-y-3">
                {available_hints.map((hint) => {
                  const revealed = revealedHintIds.has(hint.id);
                  return (
                    <div key={hint.id} className="border-t border-border pt-3 first:border-t-0 first:pt-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">Hint {hint.ordinal}</span>
                        {!revealed && !isTerminal ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={revealingHintId === hint.id}
                            onClick={() => handleRevealHint(hint.id)}
                          >
                            {revealingHintId === hint.id ? "Revealing..." : "Reveal"}
                          </Button>
                        ) : null}
                      </div>
                      {revealed ? (
                        <p className="mt-2 whitespace-pre-wrap text-sm text-muted">
                          {revealedHintMap[hint.id]}
                        </p>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="border border-border bg-surface p-4">
            <SectionLabel>Progress</SectionLabel>
            <dl className="mt-3 space-y-2 text-sm">
              {isQuiz ? null : (
                <div className="flex justify-between">
                  <dt className="text-muted">Time</dt>
                  <dd className="font-mono sl-num">{formatElapsed(elapsedSeconds)}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-muted">Hints used</dt>
                <dd>{revealedHintIds.size}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">State</dt>
                <dd className="capitalize">{attempt.status.replace("_", " ")}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>

      {submitAssessment ? (
        <AttemptResultPanel
          isCorrect={Boolean(attempt.is_correct)}
          assessment={submitAssessment}
          activityKind={isQuiz ? "quiz" : "coding"}
          readiness={readiness}
          nextAction={nextAction}
          actionState={actionState}
          actionMessage={actionMessage}
        />
      ) : null}
    </article>
  );
}
