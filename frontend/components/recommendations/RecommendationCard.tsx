"use client";

import { WhyRecommendation } from "@/components/intelligence/WhyRecommendation";
import { ButtonLink } from "@/components/ui/Button";
import { DifficultyBadge } from "@/components/problems/ProblemBadges";
import type { NextRecommendationResponse, RecommendationItem } from "@/lib/api";
import { formatMinutes } from "@/lib/catalog-ui";

export function RecommendationCard({
  data,
  showRank = false,
  compact = false,
}: {
  data: RecommendationItem;
  showRank?: boolean;
  compact?: boolean;
}) {
  const { problem } = data;

  return (
    <article className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          {showRank ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">#{data.rank}</p>
          ) : null}
          <h3 className="text-base font-semibold">{problem.title}</h3>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <DifficultyBadge difficulty={problem.difficulty} />
            <span>{formatMinutes(problem.estimated_minutes)}</span>
            <span>{problem.target_skill.name}</span>
          </div>
        </div>
        <ButtonLink href={`/problems/${problem.slug}`} size="sm">
          Start solving
        </ButtonLink>
      </div>

      {!compact ? <WhyRecommendation item={data} targetSkill={null} /> : null}
    </article>
  );
}

export function NextRecommendationSection({
  response,
}: {
  response: NextRecommendationResponse | null;
}) {
  if (!response) return null;

  if (!response.recommendation) {
    return (
      <div className="border border-border bg-surface p-4">
        <p className="sl-label">Next best problem</p>
        <p className="mt-2 text-sm text-muted">
          {response.message ?? "No recommendation available right now."}
        </p>
      </div>
    );
  }

  return (
    <section className="space-y-2">
      {response.target_skill ? (
        <p className="text-sm text-muted">
          Current focus: {response.target_skill.skill_name}
          {response.target_skill.score
            ? ` (${(parseFloat(response.target_skill.score) * 100).toFixed(0)}% mastery)`
            : " (gathering evidence)"}
        </p>
      ) : null}
      <div className="border border-border bg-surface p-4">
        <RecommendationCard data={response.recommendation} compact />
      </div>
    </section>
  );
}
