import Link from "next/link";

import { ButtonLink } from "@/components/ui/Button";
import { SectionLabel } from "@/components/ui/Primitives";
import type { TargetProfileSummary } from "@/lib/api";

export function TargetSummary({
  target,
  disclaimer,
}: {
  target: TargetProfileSummary | null;
  disclaimer: string;
}) {
  if (!target) {
    return (
      <section className="border-l-2 border-accent pl-4" aria-labelledby="target-heading">
        <SectionLabel>Target</SectionLabel>
        <h2 id="target-heading" className="mt-2 text-lg font-semibold">
          Tell SkillLens what you&apos;re preparing for.
        </h2>
        <p className="mt-2 text-sm text-muted">Choose what you&apos;re preparing for.</p>
        <div className="mt-4">
          <ButtonLink href="/account">Choose target</ButtonLink>
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="target-heading" className="flex flex-wrap items-baseline justify-between gap-3">
      <h2 id="target-heading" className="sr-only">
        Target profile
      </h2>
      <p className="max-w-2xl text-xs leading-relaxed text-muted">{disclaimer}</p>
      <Link href="/account" className="text-sm font-medium text-accent hover:underline">
        Change target
      </Link>
    </section>
  );
}
