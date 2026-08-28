import { confidenceLabel, scoreValue } from "@/lib/catalog-ui";
import { MasterySignal, SectionLabel } from "@/components/ui/Primitives";

export function MasteryConfidence({
  score,
  confidence,
}: {
  score: string | null;
  confidence: string;
}) {
  const mastery = scoreValue(score);
  const confValue = parseFloat(confidence);
  const confPct = Number.isNaN(confValue) ? 0 : Math.min(100, Math.max(0, confValue * 100));
  const confLabel = confidenceLabel(confidence);

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-baseline justify-between gap-3">
          <SectionLabel>Mastery</SectionLabel>
          <span className="sl-num text-lg font-semibold">
            {mastery === null ? "Evidence needed" : `${Math.round(mastery * 100)}% mastery`}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted">What does the evidence suggest?</p>
        <MasterySignal value={mastery} className="mt-2" />
      </div>
      <div>
        <div className="flex items-baseline justify-between gap-3">
          <SectionLabel>Confidence</SectionLabel>
          <span className="text-sm font-medium">{confLabel} confidence</span>
        </div>
        <p className="mt-1 text-xs text-muted">How strongly should we trust the assessment?</p>
        <div className="relative mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-muted">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-ink/55"
            style={{ width: `${confPct}%` }}
            aria-hidden
          />
        </div>
      </div>
    </div>
  );
}
