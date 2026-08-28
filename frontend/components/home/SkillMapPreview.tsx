import Link from "next/link";

import { SkillMap, type SkillMapNode } from "@/components/skills/SkillMap";
import { SectionLabel } from "@/components/ui/Primitives";
import type { UserSkillMasteryItem } from "@/lib/api";
import { isCoreCsSkill } from "@/lib/catalog-ui";

function chain(names: string[]): string {
  return names.join(" → ");
}

export function SkillMapPreview({
  mastery,
  edges,
  focusSlug,
}: {
  mastery: UserSkillMasteryItem[];
  edges: { from: string; to: string }[];
  focusSlug?: string | null;
}) {
  const assessed = mastery.filter((item) => item.status === "assessed" && item.score != null);
  const dsaNames = assessed.filter((item) => !isCoreCsSkill(item.topic_slug)).map((item) => item.skill_name);
  const coreNames = assessed.filter((item) => isCoreCsSkill(item.topic_slug)).map((item) => item.skill_name);

  const previewSlugs = new Set(assessed.map((item) => item.skill_slug));
  for (const edge of edges) {
    if (previewSlugs.has(edge.from) || previewSlugs.has(edge.to)) {
      previewSlugs.add(edge.from);
      previewSlugs.add(edge.to);
    }
  }

  const nodes: SkillMapNode[] = mastery
    .filter((item) => previewSlugs.has(item.skill_slug))
    .slice(0, 18)
    .map((item) => ({
      slug: item.skill_slug,
      name: item.skill_name,
      score: item.score,
      status: item.status,
      confidence: item.confidence,
    }));
  const previewEdges = edges.filter((edge) => previewSlugs.has(edge.from) && previewSlugs.has(edge.to));

  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-4">
        <div>
          <SectionLabel>Skill map</SectionLabel>
          <p className="mt-1 text-sm text-muted">Compact preview of assessed skills.</p>
        </div>
        <Link href="/skills" className="text-sm font-medium text-accent hover:underline">
          Full profile
        </Link>
      </div>
      {dsaNames.length > 0 ? (
        <p className="text-sm text-muted">
          <span className="font-medium text-ink">DSA: </span>
          {chain(dsaNames.slice(0, 6))}
        </p>
      ) : null}
      {coreNames.length > 0 ? (
        <p className="mt-1 text-sm text-muted">
          <span className="font-medium text-ink">Core CS: </span>
          {chain(coreNames.slice(0, 6))}
        </p>
      ) : null}
      {nodes.length > 0 ? (
        <div className="mt-3">
          <SkillMap nodes={nodes} edges={previewEdges} focusSlug={focusSlug} compact />
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted">The skill map fills in as evidence accumulates.</p>
      )}
    </section>
  );
}
