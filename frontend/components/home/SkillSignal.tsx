import Link from "next/link";

import { SectionLabel } from "@/components/ui/Primitives";
import type { ReadinessDimensionItem } from "@/lib/api";
import { formatScorePercent, pickSkillSignals } from "@/lib/placement-home";

export function SkillSignal({ dimensions }: { dimensions: ReadinessDimensionItem[] }) {
  const { strongest, weakest } = pickSkillSignals(dimensions);

  return (
    <section aria-labelledby="skill-signal-heading">
      <SectionLabel>Skill signal</SectionLabel>
      <h2 id="skill-signal-heading" className="sr-only">
        Skill signal
      </h2>
      {!strongest && !weakest ? (
        <p className="mt-3 text-sm text-muted">Assessed skill signals appear after DSA or Core CS evidence.</p>
      ) : (
        <div className="mt-4 grid gap-6 sm:grid-cols-2">
          {strongest ? (
            <div>
              <p className="sl-label">Strongest signal</p>
              <p className="mt-2 text-lg font-semibold">{strongest.skill_name}</p>
              <p className="sl-num mt-1 text-2xl font-semibold">{formatScorePercent(strongest.score)}</p>
              <Link
                href={`/skills/${strongest.skill_slug}`}
                className="mt-2 inline-block text-sm font-medium hover:text-accent"
              >
                {strongest.skill_name} — {formatScorePercent(strongest.score)}
              </Link>
            </div>
          ) : null}
          {weakest ? (
            <div>
              <p className="sl-label">Biggest skill gap</p>
              <p className="mt-2 text-lg font-semibold">{weakest.skill_name}</p>
              <p className="sl-num mt-1 text-2xl font-semibold">{formatScorePercent(weakest.score)}</p>
              <Link
                href={`/skills/${weakest.skill_slug}`}
                className="mt-2 inline-block text-sm font-medium hover:text-accent"
              >
                {weakest.skill_name} — {formatScorePercent(weakest.score)}
              </Link>
            </div>
          ) : null}
        </div>
      )}
      <p className="mt-4">
        <Link href="/skills" className="text-sm font-medium text-accent hover:underline">
          View skill profile →
        </Link>
      </p>
    </section>
  );
}
