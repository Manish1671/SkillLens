import Link from "next/link";

import { SectionLabel } from "@/components/ui/Primitives";
import type { PlacementActionItem, ReadinessDimensionItem, ReadinessGap } from "@/lib/api";
import {
  dimensionDisplayName,
  formatScorePercent,
  placementActionHref,
  severityLabel,
  topRankedBlockers,
} from "@/lib/placement-home";

function dimensionHref(key: string): string {
  if (key === "core_cs") return "/core-cs";
  if (key === "dsa") return "/problems";
  return "/assessment";
}

function contrastLine(dim: ReadinessDimensionItem | undefined): string | null {
  const strongest = dim?.strongest_skills?.[0];
  const weakest = dim?.weakest_actionable_skill;
  if (!strongest || !weakest) return null;
  if (strongest.skill_slug === weakest.skill_slug) return null;
  return `Your strongest evidence is in ${strongest.skill_name}, while ${weakest.skill_name} remains weak.`;
}

export function GapSummary({
  gaps,
  actions = [],
  dimensions = [],
}: {
  gaps: ReadinessGap[];
  actions?: PlacementActionItem[];
  dimensions?: ReadinessDimensionItem[];
}) {
  const blocker = topRankedBlockers(gaps, 1)[0];

  return (
    <section aria-labelledby="blockers-heading">
      <SectionLabel>Your biggest blocker</SectionLabel>
      <h2 id="blockers-heading" className="sr-only">
        Your biggest blocker
      </h2>
      {!blocker ? (
        <p className="mt-3 text-sm text-muted">No ranked blockers from the current target model.</p>
      ) : (
        (() => {
          const title = blocker.skill_name
            ? `${dimensionDisplayName(blocker.dimension)} / ${blocker.skill_name}`
            : dimensionDisplayName(blocker.dimension);
          const current = formatScorePercent(blocker.current);
          const required = formatScorePercent(blocker.required);
          const deltaPts = blocker.delta == null ? null : Math.round(blocker.delta * 100);
          const action = actions.find((item) => item.target_dimension === blocker.dimension);
          const actionHref = action ? placementActionHref(action) : dimensionHref(blocker.dimension);
          const dim = dimensions.find((item) => item.key === blocker.dimension);
          const contrast = contrastLine(dim);
          return (
            <div className="mt-3 grid gap-6 border-t border-border pt-4 lg:grid-cols-12">
              <div className="lg:col-span-5">
                <p className="text-xl font-semibold tracking-tight">{title}</p>
                <p className="mt-3 sl-num text-3xl font-semibold">{current ?? "Not assessed"}</p>
                <p className="mt-1 text-sm text-muted">
                  {required ? `→ target ${required}` : "Target not compared yet"}
                  {deltaPts != null && deltaPts < 0 ? ` · ${Math.abs(deltaPts)} points below` : null}
                </p>
                <p className="mt-3 text-xs font-semibold uppercase tracking-wide">
                  {severityLabel(blocker.severity)}
                </p>
              </div>
              <div className="lg:col-span-7">
                <p className="sl-label">Why?</p>
                <p className="mt-2 text-sm leading-relaxed text-ink">{blocker.why}</p>
                {contrast ? <p className="mt-3 text-sm leading-relaxed text-muted">{contrast}</p> : null}
                <p className="mt-4">
                  <Link href={actionHref} className="text-sm font-medium text-accent hover:underline">
                    View {dimensionDisplayName(blocker.dimension)}
                  </Link>
                </p>
              </div>
            </div>
          );
        })()
      )}
    </section>
  );
}
