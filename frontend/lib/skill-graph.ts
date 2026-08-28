export type GraphNode = {
  slug: string;
  name: string;
  x: number;
  y: number;
  layer: number;
};

export type GraphEdge = {
  from: string;
  to: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type SkillGraphLayout = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
};

const NODE_W = 148;
const NODE_H = 58;
const LAYER_GAP = 88;
const COL_GAP = 24;
const PAD = 16;

export function layoutSkillGraph(
  nodes: { slug: string; name: string }[],
  edges: { from: string; to: string }[]
): SkillGraphLayout {
  const slugs = new Set(nodes.map((n) => n.slug));
  const incoming = new Map<string, number>();
  const outgoing = new Map<string, string[]>();
  for (const node of nodes) {
    incoming.set(node.slug, 0);
    outgoing.set(node.slug, []);
  }
  const cleanEdges = edges.filter((e) => slugs.has(e.from) && slugs.has(e.to));
  for (const edge of cleanEdges) {
    incoming.set(edge.to, (incoming.get(edge.to) ?? 0) + 1);
    outgoing.get(edge.from)?.push(edge.to);
  }

  const layers: string[][] = [];
  const remaining = new Map(incoming);
  let current = nodes.filter((n) => (remaining.get(n.slug) ?? 0) === 0).map((n) => n.slug);
  const placed = new Set<string>();

  while (current.length > 0) {
    layers.push(current);
    current.forEach((slug) => placed.add(slug));
    const next: string[] = [];
    for (const slug of current) {
      for (const child of outgoing.get(slug) ?? []) {
        remaining.set(child, (remaining.get(child) ?? 1) - 1);
        if ((remaining.get(child) ?? 1) <= 0 && !placed.has(child)) {
          next.push(child);
        }
      }
    }
    current = [...new Set(next)];
  }

  const leftovers = nodes.filter((n) => !placed.has(n.slug)).map((n) => n.slug);
  if (leftovers.length) layers.push(leftovers);

  const maxCols = Math.max(1, ...layers.map((l) => l.length));
  const width = Math.max(PAD * 2 + maxCols * NODE_W + (maxCols - 1) * COL_GAP, 320);
  const height = PAD * 2 + layers.length * NODE_H + Math.max(0, layers.length - 1) * LAYER_GAP;

  const positions = new Map<string, GraphNode>();
  layers.forEach((layer, layerIndex) => {
    const layerWidth = layer.length * NODE_W + (layer.length - 1) * COL_GAP;
    const startX = (width - layerWidth) / 2;
    layer.forEach((slug, i) => {
      const node = nodes.find((n) => n.slug === slug);
      if (!node) return;
      positions.set(slug, {
        slug,
        name: node.name,
        x: startX + i * (NODE_W + COL_GAP),
        y: PAD + layerIndex * (NODE_H + LAYER_GAP),
        layer: layerIndex,
      });
    });
  });

  const laidEdges: GraphEdge[] = cleanEdges.flatMap((edge) => {
    const a = positions.get(edge.from);
    const b = positions.get(edge.to);
    if (!a || !b) return [];
    return [
      {
        from: edge.from,
        to: edge.to,
        x1: a.x + NODE_W / 2,
        y1: a.y + NODE_H,
        x2: b.x + NODE_W / 2,
        y2: b.y,
      },
    ];
  });

  return { nodes: [...positions.values()], edges: laidEdges, width, height };
}

export const SKILL_NODE = { w: NODE_W, h: NODE_H };
