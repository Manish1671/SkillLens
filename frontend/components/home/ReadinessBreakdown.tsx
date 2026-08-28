import { SectionLabel } from "@/components/ui/Primitives";
import type { ReadinessDimensionItem } from "@/lib/api";
import {
  formatScorePercent,
  matrixStateLabel,
  orderedDimensions,
} from "@/lib/placement-home";

function StateMark({ state }: { state: string }) {
  if (state === "MEETS") return <span className="text-success">✓ MEETS</span>;
  if (state === "BELOW") return <span className="text-warning">⚠ BELOW</span>;
  return <span className="text-muted">{state}</span>;
}

export function ReadinessBreakdown({ dimensions }: { dimensions: ReadinessDimensionItem[] }) {
  return (
    <section aria-labelledby="breakdown-heading">
      <SectionLabel>Readiness matrix</SectionLabel>
      <h2 id="breakdown-heading" className="sr-only">
        Readiness matrix
      </h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[32rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="sl-matrix-head py-2 pr-3 font-medium">Dimension</th>
              <th className="sl-matrix-head py-2 pr-3 font-medium">Current</th>
              <th className="sl-matrix-head py-2 pr-3 font-medium">Target</th>
              <th className="sl-matrix-head py-2 font-medium">State</th>
            </tr>
          </thead>
          <tbody>
            {orderedDimensions(dimensions).map((dim) => {
              const unassessed = dim.status === "not_assessed" || dim.score == null;
              const current = unassessed ? "—" : formatScorePercent(dim.score);
              const target =
                dim.target_min_score == null ? "—" : formatScorePercent(dim.target_min_score);
              const state = matrixStateLabel(dim);
              return (
                <tr
                  key={dim.key}
                  data-testid={`dimension-${dim.key}`}
                  className="border-b border-border/80"
                >
                  <td className="py-2.5 pr-3 font-medium">{dim.display_name}</td>
                  <td className="sl-num py-2.5 pr-3">
                    {unassessed ? <span className="text-muted">Not assessed</span> : current}
                  </td>
                  <td className="sl-num py-2.5 pr-3 text-muted">{target ?? "—"}</td>
                  <td className="py-2.5 text-xs font-semibold tracking-wide">
                    <StateMark state={state} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
