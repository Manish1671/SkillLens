"use client";

import { useCallback, useEffect, useState } from "react";

import { GapSummary } from "@/components/home/GapSummary";
import { NextActionCard } from "@/components/home/NextActionCard";
import {
  DistanceToReady,
  PlacementRiskPanel,
  ReadinessExplanation,
  ReadinessHeader,
} from "@/components/home/ReadinessHeader";
import { ReadinessBreakdown } from "@/components/home/ReadinessBreakdown";
import { RecentSignal } from "@/components/home/RecentSignal";
import { SkillMapPreview } from "@/components/home/SkillMapPreview";
import { SkillSignal } from "@/components/home/SkillSignal";
import { TargetSummary } from "@/components/home/TargetSummary";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import {
  getCurrentUser,
  getMyGaps,
  getMyMastery,
  getMyPlacementActions,
  getMyReadiness,
  listAttempts,
  type AttemptListItem,
  type PlacementActionItem,
  type PlacementReadiness,
  type ReadinessGap,
  type UserSkillMasteryItem,
} from "@/lib/api";
import { loadCatalogGraph } from "@/lib/catalog-graph";
import { mergeSkillProfile } from "@/lib/catalog-ui";

export function HomeDashboard() {
  const [readiness, setReadiness] = useState<PlacementReadiness | null>(null);
  const [gaps, setGaps] = useState<ReadinessGap[]>([]);
  const [mastery, setMastery] = useState<UserSkillMasteryItem[]>([]);
  const [edges, setEdges] = useState<{ from: string; to: string }[]>([]);
  const [attempts, setAttempts] = useState<AttemptListItem[]>([]);
  const [nextAction, setNextAction] = useState<PlacementActionItem | null>(null);
  const [actionState, setActionState] = useState<string>("ok");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actions, setActions] = useState<PlacementActionItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const user = await getCurrentUser();
    if (!user.data) {
      setLoading(false);
      return;
    }

    const [readinessResult, gapsResult, masteryResult, graph, attemptsResult, actionsResult] =
      await Promise.all([
        getMyReadiness(),
        getMyGaps(),
        getMyMastery(),
        loadCatalogGraph(),
        listAttempts({ limit: 12 }),
        getMyPlacementActions({ limit: 5 }),
      ]);

    if (readinessResult.error) {
      setError(readinessResult.error.detail);
      setLoading(false);
      return;
    }

    setReadiness(readinessResult.data ?? null);
    setGaps(gapsResult.data?.items ?? readinessResult.data?.blockers ?? []);
    setMastery(mergeSkillProfile(graph.skills, masteryResult.data?.items ?? []));
    setEdges(graph.edges);
    setAttempts(attemptsResult.data?.items ?? []);
    const listed = actionsResult.data?.items ?? [];
    setActions(listed);
    setNextAction(listed[0] ?? null);
    setActionState(actionsResult.data?.state ?? "ok");
    setActionMessage(actionsResult.data?.message ?? null);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <LoadingState message="Loading placement readiness..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
  }

  if (!readiness) {
    return <ErrorState message="Readiness could not be loaded." onRetry={load} />;
  }

  const focusSlug =
    nextAction?.target_skill?.slug ??
    readiness.dimensions.find((item) => item.key === "dsa")?.weakest_actionable_skill?.skill_slug ??
    null;
  const riskDisclaimer =
    readiness.risk_disclaimer ?? "SkillLens model — not a hiring probability.";

  return (
    <section className="space-y-10 animate-fade-in">
      <ReadinessHeader readiness={readiness} />
      <TargetSummary target={readiness.target} disclaimer={readiness.disclaimer} />

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <ReadinessBreakdown dimensions={readiness.dimensions} />
        </div>
        <div className="space-y-8 border-l-0 border-border lg:col-span-4 lg:border-l lg:pl-8">
          <DistanceToReady
            hasTarget={Boolean(readiness.target)}
            dimensions={readiness.dimensions}
            gaps={gaps}
          />
          <PlacementRiskPanel risk={readiness.risk} disclaimer={riskDisclaimer} />
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <NextActionCard action={nextAction} state={actionState} message={actionMessage} />
        </div>
        <div className="space-y-8 lg:col-span-5">
          <GapSummary gaps={gaps} actions={actions} dimensions={readiness.dimensions} />
          <ReadinessExplanation sentences={readiness.explanation ?? []} />
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <RecentSignal attempts={attempts} />
        </div>
        <div className="lg:col-span-5">
          <SkillSignal dimensions={readiness.dimensions} />
        </div>
      </div>

      <SkillMapPreview mastery={mastery} edges={edges} focusSlug={focusSlug} />
    </section>
  );
}
