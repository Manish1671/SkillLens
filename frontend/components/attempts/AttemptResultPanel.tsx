import { NextActionCard } from "@/components/home/NextActionCard";
import { ButtonLink } from "@/components/ui/Button";
import { IconCheck, IconX } from "@/components/ui/Icons";
import {
  ConfidenceBadge,
  EvidenceItem,
  MasterySignal,
  ReasonList,
  SectionLabel,
} from "@/components/ui/Primitives";
import type { ActivityKind, PlacementActionItem, PlacementReadiness, SubmitAssessmentOutcome } from "@/lib/api";
import { formatDelta } from "@/lib/catalog-ui";
import { formatScorePercent } from "@/lib/placement-home";

export function AttemptResultPanel({
  isCorrect,
  assessment,
  activityKind = "coding",
  readiness = null,
  nextAction = null,
  actionState,
  actionMessage,
}: {
  isCorrect: boolean;
  assessment: SubmitAssessmentOutcome;
  activityKind?: ActivityKind;
  readiness?: PlacementReadiness | null;
  nextAction?: PlacementActionItem | null;
  actionState?: string;
  actionMessage?: string | null;
}) {
  const primaryDelta = assessment.mastery_deltas[0];
  const reasons = assessment.recommendation?.recommendation?.explanation.sentences ?? [];
  const isQuiz = activityKind === "quiz";
  const assessedDims = (readiness?.dimensions ?? []).filter(
    (item) => item.status !== "not_assessed" && item.score != null
  );

  return (
    <section className="space-y-8 border-t border-border pt-8 animate-slide-up" aria-labelledby="attempt-result-heading">
      <header>
        <p className="sl-label">Result</p>
        <p className={`mt-2 sl-label ${isCorrect ? "text-success" : "text-danger"}`}>
          {isQuiz ? (isCorrect ? "Correct" : "Incorrect") : isCorrect ? "Solved" : "Not solved"}
        </p>
        <h2
          id="attempt-result-heading"
          className={`mt-2 text-3xl font-semibold tracking-tight ${isCorrect ? "text-success" : "text-danger"}`}
        >
          {isCorrect ? (
            <span className="inline-flex items-center gap-2">
              <IconCheck className="h-8 w-8" /> {isQuiz ? "Correct answer" : "Problem solved"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-2">
              <IconX className="h-8 w-8" /> {isQuiz ? "Incorrect answer" : "Not quite"}
            </span>
          )}
        </h2>
        <p className="mt-2 max-w-lg text-sm text-muted">
          You just taught SkillLens something about your readiness.
        </p>
      </header>

      {assessment.mastery_deltas.length > 0 ? (
        <div>
          <SectionLabel>{isQuiz ? "Core CS signal" : "Skill impact"}</SectionLabel>
          <ul className="mt-3 divide-y divide-border border-y border-border">
            {assessment.mastery_deltas.map((delta) => (
              <li key={delta.skill_slug} className="flex items-center justify-between py-3">
                <span className="font-medium">{delta.skill_name}</span>
                {delta.delta ? (
                  <span
                    className={`sl-num text-xl font-semibold ${
                      parseFloat(delta.delta) >= 0 ? "text-success" : "text-danger"
                    }`}
                  >
                    {formatDelta(delta.delta)}
                  </span>
                ) : (
                  <span className="text-sm text-muted">Gathering evidence</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {assessment.evidence_items.length > 0 ? (
        <div>
          <SectionLabel>What did SkillLens learn?</SectionLabel>
          <div className="mt-2 divide-y divide-border">
            {assessment.evidence_items.map((item) => (
              <EvidenceItem key={item.id} text={item.summary_text} polarity={item.polarity} />
            ))}
          </div>
        </div>
      ) : null}

      {primaryDelta && primaryDelta.new_score ? (
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <SectionLabel>Your current signal</SectionLabel>
            <p className="mt-2 text-sm text-muted">Mastery — what the evidence suggests</p>
            <p className="mt-1 text-lg font-semibold">{primaryDelta.skill_name}</p>
            <p className="sl-num text-4xl font-semibold tracking-tight">
              {Math.round(parseFloat(primaryDelta.new_score) * 100)}%
            </p>
            <MasterySignal value={parseFloat(primaryDelta.new_score)} className="mt-3" />
          </div>
          <div>
            <SectionLabel>Confidence</SectionLabel>
            <p className="mt-2 text-sm text-muted">How strongly we should trust that assessment</p>
            <p className="mt-3">
              <ConfidenceBadge confidence={primaryDelta.confidence} />
            </p>
          </div>
        </div>
      ) : null}

      {readiness ? (
        <div>
          <SectionLabel>Placement impact</SectionLabel>
          {assessedDims.length === 0 ? (
            <p className="mt-2 text-sm text-muted">Not enough dimension evidence yet to update readiness scores.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-sm">
              {assessedDims.map((dim) => (
                <li key={dim.key} className="flex items-baseline justify-between gap-4">
                  <span>{dim.display_name}</span>
                  <span className="sl-num">{formatScorePercent(dim.score)}</span>
                </li>
              ))}
            </ul>
          )}
          {isQuiz && readiness.blockers[0] ? (
            <p className="mt-3 text-sm leading-relaxed">{readiness.blockers[0].why}</p>
          ) : null}
        </div>
      ) : null}

      {nextAction || actionState ? (
        <NextActionCard action={nextAction} state={actionState} message={actionMessage} />
      ) : null}

      {!isQuiz && assessment.recommendation ? (
        <div className="space-y-4 border-t border-border pt-6">
          <SectionLabel>Next best problem</SectionLabel>
          {assessment.recommendation.recommendation ? (
            <>
              <h3 className="text-xl font-semibold">
                {assessment.recommendation.recommendation.problem.title}
              </h3>
              {reasons.length > 0 ? (
                <div>
                  <SectionLabel>Why?</SectionLabel>
                  <div className="mt-3">
                    <ReasonList reasons={reasons} />
                  </div>
                </div>
              ) : null}
              <ButtonLink href={`/problems/${assessment.recommendation.recommendation.problem.slug}`} size="lg">
                Start next problem
              </ButtonLink>
            </>
          ) : (
            <p className="text-sm text-muted">
              {assessment.recommendation.message ?? "No recommendation available right now."}
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
