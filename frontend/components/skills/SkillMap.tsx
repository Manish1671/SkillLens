import { layoutSkillGraph, SKILL_NODE } from "@/lib/skill-graph";
import { scoreValue, skillVisualCategory, type SkillCategory } from "@/lib/catalog-ui";

export type SkillMapNode = {
  slug: string;
  name: string;
  score?: string | null;
  status?: string;
  confidence?: string;
};

const STROKE: Record<SkillCategory, string> = {
  strong: "var(--success)",
  developing: "var(--accent)",
  needs_attention: "var(--warning)",
  insufficient: "var(--border-strong)",
};

const FILL_TEXT: Record<SkillCategory, string> = {
  strong: "var(--success)",
  developing: "var(--accent)",
  needs_attention: "var(--warning)",
  insufficient: "var(--muted)",
};

function nodeCaption(node: SkillMapNode): string {
  const score = scoreValue(node.score ?? null);
  const insufficient = node.status !== "assessed" || score === null;
  if (insufficient) return "Evidence needed";
  return `${Math.round(score * 100)}%`;
}

export function SkillMap({
  nodes,
  edges,
  focusSlug,
  compact = false,
}: {
  nodes: SkillMapNode[];
  edges: { from: string; to: string }[];
  focusSlug?: string | null;
  compact?: boolean;
}) {
  if (nodes.length === 0) return null;

  const layout = layoutSkillGraph(
    nodes.map((n) => ({ slug: n.slug, name: n.name })),
    edges
  );
  const bySlug = new Map(nodes.map((n) => [n.slug, n]));

  return (
    <div className="overflow-x-auto" data-testid="skill-map">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        width="100%"
        className={compact ? "min-w-[480px] max-w-full" : "min-w-[560px] max-w-full"}
        role="img"
        aria-label="Skill dependency map"
      >
        {layout.edges.map((edge) => {
          const midY = (edge.y1 + edge.y2) / 2;
          const isFocus = edge.from === focusSlug || edge.to === focusSlug;
          return (
            <path
              key={`${edge.from}-${edge.to}`}
              d={`M ${edge.x1} ${edge.y1} C ${edge.x1} ${midY}, ${edge.x2} ${midY}, ${edge.x2} ${edge.y2}`}
              fill="none"
              stroke={isFocus ? "var(--accent)" : "var(--border-strong)"}
              strokeWidth={isFocus ? 1.6 : 1.15}
              opacity={isFocus ? 0.9 : 0.7}
            />
          );
        })}
        {layout.nodes.map((node) => {
          const data = bySlug.get(node.slug) ?? { slug: node.slug, name: node.name };
          const category = skillVisualCategory(data);
          const focus = node.slug === focusSlug;
          const score = scoreValue(data.score ?? null);
          const weight = category === "strong" ? 1 : category === "needs_attention" ? 0.95 : category === "insufficient" ? 0.62 : 0.85;
          const title = [
            data.name,
            score == null ? "Not enough evidence" : `${Math.round(score * 100)}% mastery`,
            data.confidence ? `Confidence ${Math.round(parseFloat(data.confidence) * 100)}%` : null,
          ]
            .filter(Boolean)
            .join(" · ");
          return (
            <a key={node.slug} href={`/skills/${node.slug}`}>
              <g className="cursor-pointer">
                <title>{title}</title>
                {focus ? (
                  <>
                    <rect
                      x={node.x - 7}
                      y={node.y - 7}
                      width={SKILL_NODE.w + 14}
                      height={SKILL_NODE.h + 14}
                      rx="12"
                      fill="none"
                      stroke="var(--accent)"
                      strokeWidth="1.15"
                      opacity="0.45"
                    />
                    <rect
                      x={node.x - 3}
                      y={node.y - 3}
                      width={SKILL_NODE.w + 6}
                      height={SKILL_NODE.h + 6}
                      rx="10"
                      fill="var(--accent-soft)"
                      stroke="var(--accent)"
                      strokeWidth="1.4"
                    />
                  </>
                ) : null}
                <rect
                  x={node.x}
                  y={node.y}
                  width={SKILL_NODE.w}
                  height={SKILL_NODE.h}
                  rx="8"
                  fill="var(--surface)"
                  stroke={focus ? "var(--accent)" : STROKE[category]}
                  strokeWidth={focus ? 1.9 : category === "strong" ? 1.6 : 1.15}
                  opacity={weight}
                />
                <text
                  x={node.x + 12}
                  y={node.y + 22}
                  fill="var(--foreground)"
                  fontSize={category === "insufficient" && !focus ? "11" : "12"}
                  fontWeight="600"
                >
                  {node.name.length > 16 ? `${node.name.slice(0, 15)}…` : node.name}
                </text>
                <text
                  x={node.x + 12}
                  y={node.y + 42}
                  fill={FILL_TEXT[category]}
                  fontSize="11"
                  fontFamily="ui-monospace, monospace"
                >
                  {nodeCaption(data)}
                </text>
              </g>
            </a>
          );
        })}
      </svg>
    </div>
  );
}
