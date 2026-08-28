"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SkillMap, type SkillMapNode } from "@/components/skills/SkillMap";
import { ButtonLink } from "@/components/ui/Button";
import {
  ConfidenceBadge,
  MasterySignal,
  SectionLabel,
} from "@/components/ui/Primitives";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/ui/StatePanels";
import { AuthGate } from "@/hooks/useRequireAuth";
import { getMyMastery, getNextRecommendation, type UserSkillMasteryItem } from "@/lib/api";
import { loadCatalogGraph } from "@/lib/catalog-graph";
import {
  CATEGORY_LABELS,
  categorizeSkill,
  confidenceLabel,
  mergeSkillProfile,
  scoreValue,
  type SkillCategory,
  isCoreCsSkill,
} from "@/lib/catalog-ui";

function SkillTile({ item }: { item: UserSkillMasteryItem }) {
  const score = scoreValue(item.score);
  const insufficient = item.status !== "assessed" || score === null;
  const category = categorizeSkill(item);

  return (
    <Link
      href={`/skills/${item.skill_slug}`}
      className="block border-b border-r border-border p-3.5 transition-colors hover:bg-white"
      data-testid={`skill-card-${item.skill_slug}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold leading-snug">{item.skill_name}</p>
        <span className="sl-num shrink-0 text-sm font-semibold">
          {insufficient ? "—" : `${Math.round(score * 100)}%`}
        </span>
      </div>
      <p className="mt-1 text-[11px] uppercase tracking-wider text-muted">
        {CATEGORY_LABELS[category]}
      </p>
      {insufficient ? (
        <p className="mt-2 text-xs text-muted">Evidence needed</p>
      ) : (
        <>
          <p className="mt-2 sl-num text-xs text-ink">
            {Math.round(score * 100)}% mastery
            <span className="mx-1.5 text-muted">·</span>
            {confidenceLabel(item.confidence)} confidence
          </p>
          <MasterySignal value={score} className="mt-2" />
          <div className="mt-2 flex items-center justify-between text-xs text-muted">
            <ConfidenceBadge confidence={item.confidence} />
            <span>
              {item.evidence_count} evidence
            </span>
          </div>
        </>
      )}
    </Link>
  );
}

function SkillsProfile() {
  const [items, setItems] = useState<UserSkillMasteryItem[]>([]);
  const [edges, setEdges] = useState<{ from: string; to: string }[]>([]);
  const [graphFilter, setGraphFilter] = useState<"all" | "dsa" | "core_cs">("all");
  const [focusSlug, setFocusSlug] = useState<string | null>(null);
  const [focusName, setFocusName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    const [masteryResult, graph, nextResult] = await Promise.all([
      getMyMastery(),
      loadCatalogGraph(),
      getNextRecommendation(),
    ]);
    if (masteryResult.status === 401) {
      setLoading(false);
      return;
    }
    if (masteryResult.error) {
      setError(masteryResult.error.detail);
      setLoading(false);
      return;
    }
    setItems(mergeSkillProfile(graph.skills, masteryResult.data?.items ?? []));
    setEdges(graph.edges);
    setFocusSlug(nextResult.data?.target_skill?.skill_slug ?? null);
    setFocusName(nextResult.data?.target_skill?.skill_name ?? null);
    setLoading(false);
  }

  if (loading) {
    return <LoadingState message="Loading your skill profile..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
  }

  const grouped = items.reduce<Record<SkillCategory, UserSkillMasteryItem[]>>(
    (acc, item) => {
      acc[categorizeSkill(item)].push(item);
      return acc;
    },
    { strong: [], developing: [], needs_attention: [], insufficient: [] }
  );

  const counts = {
    strong: grouped.strong.length,
    developing: grouped.developing.length,
    needs_attention: grouped.needs_attention.length,
    insufficient: grouped.insufficient.length,
  };

  const strongest = items
    .filter((item) => item.status === "assessed" && item.score != null)
    .sort((a, b) => parseFloat(b.score ?? "0") - parseFloat(a.score ?? "0"))[0];
  const assessedCount = items.filter((item) => item.status === "assessed" && item.score !== null).length;
  const evidenceCollected = items.reduce((sum, item) => sum + item.evidence_count, 0);
  const hasAnyEvidence = evidenceCollected > 0;

  const mapNodes: SkillMapNode[] = items
    .filter((item) => {
      if (graphFilter === "dsa") return !isCoreCsSkill(item.topic_slug);
      if (graphFilter === "core_cs") return isCoreCsSkill(item.topic_slug);
      return true;
    })
    .map((item) => ({
      slug: item.skill_slug,
      name: item.skill_name,
      score: item.score,
      status: item.status,
      confidence: item.confidence,
    }));
  const mapSlugs = new Set(mapNodes.map((node) => node.slug));
  const mapEdges = edges.filter((edge) => mapSlugs.has(edge.from) && mapSlugs.has(edge.to));

  return (
    <div className="space-y-8" data-testid="skill-profile">
      <PageHeader
        eyebrow="Skill intelligence"
        title="Your Skill Profile"
        description="Your abilities, reconstructed from evidence."
      />

      {!hasAnyEvidence ? (
        <div className="border border-border bg-surface px-5 py-5" data-testid="skills-empty-onboarding">
          <p className="sl-eyebrow">Getting started</p>
          <h2 className="mt-2 text-lg font-semibold">Your skill model starts with your first attempt.</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            Foundational skills are shown below as evidence-needed until you submit work. Nothing here is invented —
            SkillLens waits for real attempts.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <ButtonLink href="/assessment">Assess Me</ButtonLink>
            <ButtonLink href="/problems" variant="secondary">
              Start with a problem
            </ButtonLink>
          </div>
        </div>
      ) : null}

      <section className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border sm:grid-cols-4">
        {(
          [
            ["strong", counts.strong],
            ["developing", counts.developing],
            ["needs_attention", counts.needs_attention],
            ["insufficient", counts.insufficient],
          ] as const
        ).map(([key, count]) => (
          <div key={key} className="bg-surface px-4 py-4">
            <p className="sl-num text-2xl font-semibold">{count}</p>
            <p className="mt-1 text-xs text-muted">{CATEGORY_LABELS[key]}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 border-y border-border py-4 sm:grid-cols-4">
        <div>
          <SectionLabel>Skills assessed</SectionLabel>
          <p className="mt-1 sl-num text-lg font-semibold">
            {assessedCount} / {items.length}
          </p>
        </div>
        <div>
          <SectionLabel>Evidence collected</SectionLabel>
          <p className="mt-1 sl-num text-lg font-semibold">{evidenceCollected}</p>
        </div>
        <div>
          <SectionLabel>Current focus</SectionLabel>
          <p className="mt-1 text-lg font-semibold">{focusName ?? "Not yet determined"}</p>
        </div>
        <div>
          <SectionLabel>Strongest skill</SectionLabel>
          <p className="mt-1 text-lg font-semibold">{strongest?.skill_name ?? "Not yet determined"}</p>
        </div>
      </section>

      <section>
        <SectionLabel>Skill map</SectionLabel>
        <p className="mt-1 text-sm text-muted">
          {hasAnyEvidence
            ? "Each node is part of your skill model. Current focus is ringed."
            : "This is the dependency graph your evidence will fill in."}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(
            [
              ["all", "All"],
              ["dsa", "DSA"],
              ["core_cs", "Core CS"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                graphFilter === value ? "bg-ink text-white" : "bg-surface-muted text-muted"
              }`}
              onClick={() => setGraphFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="mt-4">
          <SkillMap nodes={mapNodes} edges={mapEdges} focusSlug={focusSlug} />
        </div>
      </section>

      {items.length === 0 ? (
        <EmptyState
          title="Your skill model starts with your first attempt."
          description="The catalog is empty in this environment. Seed skills, then return here."
        />
      ) : (
        <>
          <section>
            {(
              [
                ["strong", grouped.strong],
                ["developing", grouped.developing],
                ["needs_attention", grouped.needs_attention],
                ["insufficient", grouped.insufficient],
              ] as const
            ).map(([key, group]) =>
              group.length === 0 ? null : (
                <section key={key} className="mt-8">
                  <SectionLabel>{CATEGORY_LABELS[key]}</SectionLabel>
                  <div className="mt-3 grid grid-cols-1 overflow-hidden border-t border-border sm:grid-cols-2 lg:grid-cols-3">
                    {group.map((item) => (
                      <SkillTile key={item.skill_slug} item={item} />
                    ))}
                  </div>
                </section>
              )
            )}
          </section>
        </>
      )}
    </div>
  );
}

export function SkillsPageContent() {
  return (
    <AuthGate nextPath="/skills">
      {() => <SkillsProfile />}
    </AuthGate>
  );
}
