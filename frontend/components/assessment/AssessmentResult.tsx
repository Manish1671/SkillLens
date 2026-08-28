"use client";

import { NextActionCard } from "@/components/home/NextActionCard";
import { ButtonLink } from "@/components/ui/Button";
import { ReasonList, SectionLabel } from "@/components/ui/Primitives";
import type { GapListResponse, PlacementActionItem, PlacementReadiness, UserSkillMasteryItem } from "@/lib/api";
import {
  assessmentSummaryCounts,
  dimensionScoreLine,
  howDidWeAssessYou,
  profileHeadline,
} from "@/lib/assessment-explain";
import {
  orderedDimensions,
  severityLabel,
  topRankedBlockers,
} from "@/lib/placement-home";

export function AssessmentResult({
  planDsaCount,
  planCsCount,
  readiness,
  gaps,
  mastery,
  action,
  actionState,
  actionMessage,
}: {
  planDsaCount: number;
  planCsCount: number;
  readiness: PlacementReadiness | null;
  gaps: GapListResponse | null;
  mastery: UserSkillMasteryItem[];
  action: PlacementActionItem | null;
  actionState: string | undefined;
  actionMessage: string | null | undefined;
}) {
  const headline = profileHeadline(readiness);
  const counts = assessmentSummaryCounts(mastery, readiness);
  const blockers = topRankedBlockers(gaps?.items ?? [], 3);
  const dimensions = orderedDimensions(readiness?.dimensions ?? []);
  const how = howDidWeAssessYou({
    targetName: readiness?.target?.name ?? null,
    dsaAssessed: counts.dsaEvidence,
    csAssessed: counts.csEvidence,
    planDsaCount,
    planCsCount,
  });

  return (
    <div className="space-y-8" data-testid="assessment-complete">
      <header>
        <p className="sl-eyebrow">Assessment complete</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Your initial placement profile</h1>
        <p className="mt-2 max-w-xl text-sm text-muted">
          This is a SkillLens baseline from the evidence just collected — not a claim of hireability.
        </p>
      </header>

      <section className="border-y border-border py-4">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Target</dt>
            <dd className="mt-1 font-semibold">{headline.targetName}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Placement state</dt>
            <dd className="mt-1 font-semibold">{headline.stateLabel}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Confidence</dt>
            <dd className="mt-1 font-semibold">{headline.confidenceLabel}</dd>
          </div>
        </dl>
      </section>

      <section>
        <SectionLabel>Readiness breakdown</SectionLabel>
        <div className="mt-3 divide-y divide-border border-y border-border">
          {dimensions.map((item) => (
            <div key={item.key} className="flex flex-wrap items-baseline justify-between gap-2 bg-surface px-4 py-3">
              <p className="font-medium">{item.display_name}</p>
              <p className="text-sm text-muted">
                {item.key === "projects" || item.key === "interview" || item.key === "profile" || item.status === "not_assessed"
                  ? "Not assessed"
                  : dimensionScoreLine(item.score, item.status)}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border sm:grid-cols-4">
        <div className="bg-surface px-4 py-4">
          <p className="sl-num text-2xl font-semibold">{counts.dsaEvidence}</p>
          <p className="mt-1 text-xs text-muted">DSA evidence</p>
        </div>
        <div className="bg-surface px-4 py-4">
          <p className="sl-num text-2xl font-semibold">{counts.csEvidence}</p>
          <p className="mt-1 text-xs text-muted">Core CS evidence</p>
        </div>
        <div className="bg-surface px-4 py-4">
          <p className="sl-num text-2xl font-semibold">{counts.skillsAssessed}</p>
          <p className="mt-1 text-xs text-muted">Skills assessed</p>
        </div>
        <div className="bg-surface px-4 py-4">
          <p className="sl-num text-2xl font-semibold">{counts.skillsInsufficient}</p>
          <p className="mt-1 text-xs text-muted">Skills still insufficient</p>
        </div>
      </section>

      {blockers.length > 0 ? (
        <section>
          <SectionLabel>Biggest gaps</SectionLabel>
          <ul className="mt-3 space-y-3">
            {blockers.map((gap) => (
              <li key={`${gap.dimension}-${gap.skill_slug ?? "dim"}-${gap.rank}`} className="border-t border-border py-4">
                <p className="font-medium">
                  {gap.skill_name ?? gap.dimension.replace("_", " ")}
                </p>
                <p className="mt-1 text-sm text-muted">{gap.why}</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-muted">{severityLabel(gap.severity)}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div data-testid="assessment-next">
        <NextActionCard action={action} state={actionState} message={actionMessage} />
      </div>

      <section>
        <SectionLabel>How did we assess you?</SectionLabel>
        <div className="mt-3">
          <ReasonList reasons={how} />
        </div>
      </section>

      <ButtonLink href="/" variant="secondary">
        Open command center
      </ButtonLink>
    </div>
  );
}
