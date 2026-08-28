"use client";

import { Button } from "@/components/ui/Button";

export function AssessmentIntro({
  targetName,
  onBegin,
  canResume,
  onResume,
}: {
  targetName: string | null;
  onBegin: () => void;
  canResume: boolean;
  onResume: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl space-y-5" data-testid="assessment-intro">
      <p className="sl-page-kicker">Assess</p>
      <h1 className="text-3xl font-semibold tracking-tight">Assess your placement readiness</h1>
      <p className="text-sm leading-relaxed text-muted">
        Answer a small set of representative questions so SkillLens can establish your current baseline.
      </p>
      <p className="text-sm leading-relaxed text-muted">
        SkillLens will ask a short mix of DSA problems and Core CS quizzes. Each answer is a normal
        attempt — the same evidence, mastery, readiness, and placement-action pipeline you use afterwards.
      </p>
      {targetName ? (
        <p className="text-sm text-muted">
          Measured against <span className="font-medium text-ink">{targetName}</span>. This is a baseline,
          not a hiring prediction.
        </p>
      ) : null}
      <div className="flex flex-wrap gap-3">
        {canResume ? (
          <Button onClick={onResume}>Resume</Button>
        ) : (
          <Button onClick={onBegin}>Begin</Button>
        )}
      </div>
    </div>
  );
}
