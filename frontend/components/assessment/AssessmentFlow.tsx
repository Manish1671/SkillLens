"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AssessmentIntro } from "@/components/assessment/AssessmentIntro";
import { AssessmentQuestion } from "@/components/assessment/AssessmentQuestion";
import { AssessmentResult } from "@/components/assessment/AssessmentResult";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { AuthGate } from "@/hooks/useRequireAuth";
import {
  getAssessmentPlan,
  getMyGaps,
  getMyMastery,
  getMyReadiness,
  getNextPlacementAction,
  getProblem,
  startAttempt,
  submitAttempt,
  type AssessmentPlanResponse,
  type GapListResponse,
  type PlacementActionItem,
  type PlacementReadiness,
  type ProblemDetail,
  type PublicUser,
  type UserSkillMasteryItem,
} from "@/lib/api";
import {
  clientAttemptId,
  loadAssessmentSession,
  saveAssessmentSession,
  type StoredAssessmentSession,
} from "@/lib/assessment-session";

type Phase = "intro" | "loading" | "question" | "complete" | "error";

function AssessmentExperience({ user }: { user: PublicUser }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dimension = searchParams.get("dimension");
  const [phase, setPhase] = useState<Phase>("intro");
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<AssessmentPlanResponse | null>(null);
  const [index, setIndex] = useState(0);
  const [sessionNumber, setSessionNumber] = useState(1);
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState(0);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [readiness, setReadiness] = useState<PlacementReadiness | null>(null);
  const [gaps, setGaps] = useState<GapListResponse | null>(null);
  const [mastery, setMastery] = useState<UserSkillMasteryItem[]>([]);
  const [action, setAction] = useState<PlacementActionItem | null>(null);
  const [actionState, setActionState] = useState<string | undefined>();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [stored, setStored] = useState<StoredAssessmentSession | null>(null);
  const skippedSubmitted = useRef<string | null>(null);

  const persist = useCallback(
    (next: Partial<StoredAssessmentSession> & { plan: AssessmentPlanResponse }) => {
      const payload: StoredAssessmentSession = {
        userId: user.id,
        assessmentId: next.plan.assessment_id ?? "",
        dimension,
        session: next.session ?? sessionNumber,
        index: next.index ?? index,
        complete: next.complete ?? false,
        plan: next.plan,
      };
      saveAssessmentSession(payload);
      setStored(payload);
    },
    [dimension, index, sessionNumber, user.id]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const existing = loadAssessmentSession(user.id);
      setStored(existing);
      const result = await getAssessmentPlan({ dimension });
      if (cancelled) return;
      if (result.error) {
        setError(result.error.detail);
        setPhase("error");
        return;
      }
      const data = result.data;
      if (!data || data.state === "no_target") {
        router.replace("/account?reason=assessment");
        return;
      }
      setPlan(data);
      if (
        existing &&
        !existing.complete &&
        existing.assessmentId === data.assessment_id &&
        existing.index < data.total_items
      ) {
        setPlan(existing.plan);
        setIndex(existing.index);
        setSessionNumber(existing.session);
        setPhase("question");
      }
    })();
    return () => {
      cancelled = true;
    };
    // router.replace is used for the no-target redirect; omit router from deps
    // so Next.js' unstable router identity cannot retrigger this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dimension, user.id]);

  const currentItem = plan?.items[index];

  useEffect(() => {
    if (phase !== "question" || !currentItem || !plan?.assessment_id) return;
    let cancelled = false;
    (async () => {
      setError(null);
      setProblem(null);
      setAttemptId(null);
      setIsCorrect(null);
      setSelectedOption(null);
      const detail = await getProblem(currentItem.problem_slug);
      if (cancelled) return;
      if (!detail.data) {
        setError(detail.error?.detail ?? "Problem could not be loaded.");
        setPhase("error");
        return;
      }
      const started = await startAttempt({
        problem_id: detail.data.id,
        client_attempt_id: clientAttemptId(plan.assessment_id ?? "", currentItem.position, sessionNumber),
      });
      if (cancelled) return;
      if (!started.data) {
        setError(started.error?.detail ?? "Could not start assessment attempt.");
        setPhase("error");
        return;
      }
      if (started.data.status === "submitted") {
        const skipKey = `${plan.assessment_id}:${currentItem.position}`;
        if (skippedSubmitted.current !== skipKey) {
          skippedSubmitted.current = skipKey;
          await goNext();
        }
        return;
      }
      setProblem(detail.data);
      setAttemptId(started.data.id);
      setStartedAt(Date.now());
    })();
    return () => {
      cancelled = true;
    };
    // goNext is stable enough via index; we intentionally freeze the plan snapshot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, currentItem?.problem_slug, plan?.assessment_id, sessionNumber, index]);

  async function finish(activePlan: AssessmentPlanResponse) {
    setPhase("loading");
    persist({ plan: activePlan, index: activePlan.total_items, complete: true, session: sessionNumber });
    const [readinessResult, gapsResult, masteryResult, actionResult] = await Promise.all([
      getMyReadiness(),
      getMyGaps(),
      getMyMastery(),
      getNextPlacementAction({ refresh: true }),
    ]);
    setReadiness(readinessResult.data ?? null);
    setGaps(gapsResult.data ?? null);
    setMastery(masteryResult.data?.items ?? []);
    setAction(actionResult.data?.action ?? null);
    setActionState(actionResult.data?.state);
    setActionMessage(actionResult.data?.message ?? null);
    setPhase("complete");
  }

  async function goNext() {
    if (!plan) return;
    if (index + 1 >= plan.total_items) {
      await finish(plan);
      return;
    }
    const nextIndex = index + 1;
    setIndex(nextIndex);
    persist({ plan, index: nextIndex, session: sessionNumber, complete: false });
    setAttemptId(null);
    setProblem(null);
  }

  async function begin(resume: boolean) {
    setPhase("loading");
    setError(null);
    const result = await getAssessmentPlan({ dimension });
    if (result.error || !result.data) {
      setError(result.error?.detail ?? "Could not load the assessment plan.");
      setPhase("error");
      return;
    }
    if (result.data.state === "no_target") {
      router.replace("/account?reason=assessment");
      return;
    }
    const nextSession =
      resume && stored && stored.assessmentId === result.data.assessment_id
        ? stored.session
        : stored?.complete
          ? stored.session + 1
          : 1;
    const startIndex = resume && stored && !stored.complete ? stored.index : 0;
    const snapshot = resume && stored && !stored.complete ? stored.plan : result.data;
    setPlan(snapshot);
    setSessionNumber(nextSession);
    setIndex(startIndex);
    persist({
      plan: snapshot,
      index: startIndex,
      session: nextSession,
      complete: false,
    });
    setPhase("question");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!attemptId || !currentItem) return;
    const isQuiz = currentItem.activity_kind === "quiz";
    if (isQuiz && !selectedOption) return;
    if (!isQuiz && isCorrect === null) return;
    setSubmitting(true);
    const seconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
    const result = await submitAttempt(
      attemptId,
      isQuiz
        ? { selected_option: selectedOption ?? undefined, time_spent_seconds: seconds }
        : { is_correct: isCorrect ?? false, time_spent_seconds: seconds }
    );
    setSubmitting(false);
    if (result.error) {
      setError(result.error.detail);
      return;
    }
    await goNext();
  }

  if (phase === "intro") {
    return (
      <AssessmentIntro
        targetName={plan?.target?.name ?? null}
        canResume={Boolean(stored && !stored.complete && stored.assessmentId === plan?.assessment_id)}
        onBegin={() => void begin(false)}
        onResume={() => void begin(true)}
      />
    );
  }

  if (phase === "loading") {
    return <LoadingState message="Preparing your placement assessment..." />;
  }

  if (phase === "error") {
    return <ErrorState message={error ?? "Something went wrong."} onRetry={() => void begin(false)} />;
  }

  if (phase === "complete") {
    const dsaCount = plan?.items.filter((item) => item.dimension === "dsa").length ?? 0;
    const csCount = plan?.items.filter((item) => item.dimension === "core_cs").length ?? 0;
    return (
      <AssessmentResult
        planDsaCount={dsaCount}
        planCsCount={csCount}
        readiness={readiness}
        gaps={gaps}
        mastery={mastery}
        action={action}
        actionState={actionState}
        actionMessage={actionMessage}
      />
    );
  }

  if (!problem || !currentItem) {
    return <LoadingState message="Loading question..." />;
  }

  return (
    <AssessmentQuestion
      problem={problem}
      index={index}
      total={plan?.total_items ?? 0}
      dimension={currentItem.dimension}
      error={error}
      submitting={submitting}
      isQuiz={currentItem.activity_kind === "quiz"}
      isCorrect={isCorrect}
      selectedOption={selectedOption}
      onCorrectChange={setIsCorrect}
      onSelectOption={setSelectedOption}
      onSubmit={(event) => void handleSubmit(event)}
    />
  );
}

export function AssessmentFlow() {
  const searchParams = useSearchParams();
  const dimension = searchParams.get("dimension");
  const nextPath = dimension ? `/assessment?dimension=${dimension}` : "/assessment";
  return <AuthGate nextPath={nextPath}>{(user) => <AssessmentExperience user={user} />}</AuthGate>;
}
