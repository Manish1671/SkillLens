"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { WhyFromNextResponse } from "@/components/intelligence/WhyRecommendation";
import { MasteryConfidence } from "@/components/intelligence/MasteryConfidence";
import { RecentTrend } from "@/components/intelligence/RecentTrend";
import { NextRecommendationSection } from "@/components/recommendations/RecommendationCard";
import { SkillMap } from "@/components/skills/SkillMap";
import { ButtonLink } from "@/components/ui/Button";
import {
  EvidenceTimeline,
  SectionLabel,
  Sparkline,
} from "@/components/ui/Primitives";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { AuthGate } from "@/hooks/useRequireAuth";
import { getMySkillDetail, getNextRecommendation, type UserSkillDetail } from "@/lib/api";
import { formatScore, isPrerequisiteReady, scoreValue } from "@/lib/catalog-ui";
import { recentTrendFromSnapshots } from "@/lib/recent-trend";

function SkillReport({ slug }: { slug: string }) {
  const [detail, setDetail] = useState<UserSkillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skillRecommendation, setSkillRecommendation] = useState<
    Awaited<ReturnType<typeof getNextRecommendation>>["data"] | null
  >(null);

  useEffect(() => {
    async function load() {
      const result = await getMySkillDetail(slug);
      if (result.status === 401) {
        setLoading(false);
        return;
      }
      if (result.error) {
        setError(result.error.detail);
        setLoading(false);
        return;
      }
      setDetail(result.data ?? null);
      const rec = await getNextRecommendation({ target_skill: slug });
      setSkillRecommendation(rec.data ?? null);
      setLoading(false);
    }
    load();
  }, [slug]);

  if (loading) {
    return <LoadingState message="Loading skill report..." />;
  }

  if (error || !detail) {
    return <ErrorState message={error ?? "Skill not found."} />;
  }

  const score = scoreValue(detail.score);
  const sparkValues = [...detail.snapshots]
    .slice()
    .sort((a, b) => a.computed_at.localeCompare(b.computed_at))
    .map((snap) => parseFloat(snap.score))
    .filter((n) => !Number.isNaN(n));
  const trend = recentTrendFromSnapshots(detail.snapshots);
  const blocking = detail.prerequisites.filter(
    (prereq) => !isPrerequisiteReady(prereq.score, prereq.status)
  );

  const mapNodes = [
    ...detail.prerequisites.map((p) => ({
      slug: p.skill_slug,
      name: p.skill_name,
      score: p.score,
      status: p.status,
      confidence: p.confidence,
    })),
    {
      slug: detail.slug,
      name: detail.name,
      score: detail.score,
      status: detail.status,
      confidence: detail.confidence,
    },
    ...detail.dependents.map((d) => ({
      slug: d.skill_slug,
      name: d.skill_name,
      score: d.score,
      status: d.status,
      confidence: d.confidence,
    })),
  ];
  const mapEdges = [
    ...detail.prerequisites.map((p) => ({ from: p.skill_slug, to: detail.slug })),
    ...detail.dependents.map((d) => ({ from: detail.slug, to: d.skill_slug })),
  ];

  return (
    <article className="space-y-8" data-testid="skill-report">
      <nav className="text-sm text-muted">
        <Link href="/skills" className="hover:text-accent">
          Skills
        </Link>
        <span className="mx-2">/</span>
        <span className="text-ink">{detail.name}</span>
      </nav>

      <header className="grid gap-6 border-b border-border pb-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <p className="sl-eyebrow">Evidence report</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{detail.name}</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">{detail.description}</p>
          {score === null ? (
            <p className="mt-4 text-sm text-muted">
              Evidence needed. Complete a problem that exercises this skill to create a signal.
            </p>
          ) : null}
        </div>
        <div className="lg:col-span-5">
          <MasteryConfidence score={detail.score} confidence={detail.confidence} />
          <div className="mt-4">
            <RecentTrend trend={trend} />
          </div>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-12">
        <section className="lg:col-span-7 space-y-8">
          <div>
            <SectionLabel>Mastery history</SectionLabel>
            <div className="mt-3">
              <Sparkline values={sparkValues} label={`${detail.name} mastery history`} />
            </div>
          </div>

          <div>
            <SectionLabel>What the evidence says</SectionLabel>
            <div className="mt-3" data-testid="skill-evidence-timeline">
              <EvidenceTimeline
                items={detail.evidence_timeline.map((item) => ({
                  id: item.id,
                  text: item.summary_text,
                  polarity: item.polarity,
          meta: `${new Date(item.created_at).toLocaleString()} · ${item.evidence_type.replace(/_/g, " ")}`,
                }))}
              />
            </div>
          </div>
        </section>

        <aside className="space-y-6 lg:col-span-5">
          {detail.prerequisites.length > 0 ? (
            <section>
              <SectionLabel>Prerequisite signal</SectionLabel>
              {blocking.length > 0 ? (
                <p className="mt-2 text-xs text-warning">
                  {blocking.map((p) => p.skill_name).join(", ")}{" "}
                  {blocking.length === 1 ? "is" : "are"} not ready yet and may be blocking this skill.
                </p>
              ) : (
                <p className="mt-2 text-xs text-muted">Supporting skills look ready for this work.</p>
              )}
              <ul className="mt-3 divide-y divide-border border border-border bg-surface">
                {detail.prerequisites.map((prereq) => {
                  const ready = isPrerequisiteReady(prereq.score, prereq.status);
                  return (
                    <li key={prereq.skill_slug}>
                      <Link
                        href={`/skills/${prereq.skill_slug}`}
                        className="flex items-center justify-between px-4 py-3 text-sm hover:bg-white"
                      >
                        <span className="font-medium">{prereq.skill_name}</span>
                        <span className={`sl-num ${ready ? "text-success" : "text-muted"}`}>
                          {prereq.score === null
                            ? "Evidence needed"
                            : `${formatScore(prereq.score)} ${ready ? "✓ Ready" : "Blocking"}`}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          ) : null}

          {mapNodes.length > 1 ? (
            <section>
              <SectionLabel>Local graph</SectionLabel>
              <div className="mt-3">
                <SkillMap nodes={mapNodes} edges={mapEdges} focusSlug={detail.slug} compact />
              </div>
            </section>
          ) : null}

          <section>
            <SectionLabel>Next practice</SectionLabel>
            <div className="mt-3">
              <NextRecommendationSection response={skillRecommendation ?? null} />
              {skillRecommendation?.recommendation ? (
                <div className="mt-4 border border-border bg-surface p-4">
                  <WhyFromNextResponse response={skillRecommendation} />
                </div>
              ) : (
                <ButtonLink href="/assessment" variant="secondary" className="mt-3">
                  Assess Me
                </ButtonLink>
              )}
            </div>
          </section>
        </aside>
      </div>
    </article>
  );
}

export function SkillDetailPageContent({ slug }: { slug: string }) {
  return (
    <AuthGate nextPath={`/skills/${slug}`}>
      {() => <SkillReport slug={slug} />}
    </AuthGate>
  );
}
