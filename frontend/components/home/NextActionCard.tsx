import { ButtonLink } from "@/components/ui/Button";
import { IconArrowRight } from "@/components/ui/Icons";
import { ReasonList, SectionLabel } from "@/components/ui/Primitives";
import type { PlacementActionItem } from "@/lib/api";
import { formatMinutes } from "@/lib/catalog-ui";
import { dimensionDisplayName, placementActionHref, placementActionLabel } from "@/lib/placement-home";

export function NextActionCard({
  action,
  state,
  message,
}: {
  action: PlacementActionItem | null;
  state?: string;
  message?: string | null;
}) {
  if (state === "no_target" || (!action && state === "no_target")) {
    return (
      <section className="border-l-2 border-accent pl-5" aria-labelledby="next-action-heading">
        <SectionLabel>Next best action</SectionLabel>
        <p className="sl-eyebrow mt-3">Your next move</p>
        <h2 id="next-action-heading" className="mt-2 text-xl font-semibold">
          Choose a target profile
        </h2>
        <p className="mt-2 text-sm text-muted">
          {message ?? "Readiness actions are evaluated against a selected SkillLens target."}
        </p>
        <div className="mt-4">
          <ButtonLink href="/account">Choose target</ButtonLink>
        </div>
      </section>
    );
  }

  if (!action) {
    return (
      <section className="border-l-2 border-accent pl-5" aria-labelledby="next-action-heading">
        <SectionLabel>Next best action</SectionLabel>
        <p className="sl-eyebrow mt-3">Your next move</p>
        <h2 id="next-action-heading" className="mt-2 text-xl font-semibold">
          No eligible placement action
        </h2>
        <p className="mt-2 text-sm text-muted">
          {message ?? "Generate evidence against your target to unlock a next action."}
        </p>
        <div className="mt-4">
          <ButtonLink href="/assessment">Assess Me</ButtonLink>
        </div>
      </section>
    );
  }

  const href = placementActionHref(action);
  const cta =
    action.action_kind === "assess_dimension"
      ? "Start assessment"
      : action.action_kind === "cs_quiz"
        ? "Start quiz"
        : "Start";

  return (
    <section className="border-l-2 border-accent pl-5" aria-labelledby="next-action-heading">
      <SectionLabel>{placementActionLabel(action.action_kind)}</SectionLabel>
      <p className="sl-eyebrow mt-3">Next best action</p>
      <p className="mt-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted">Your next move</p>
      <h2 id="next-action-heading" className="mt-2 text-2xl font-semibold tracking-tight">
        {action.title}
      </h2>
      <p className="mt-3 text-sm text-muted">
        {dimensionDisplayName(action.target_dimension)}
        {action.target_skill?.name ? ` · ${action.target_skill.name}` : ""}
        {` · ${formatMinutes(action.estimated_effort_minutes)}`}
      </p>
      {action.why.length > 0 ? (
        <div className="mt-5">
          <SectionLabel>Why this?</SectionLabel>
          <div className="mt-3">
            <ReasonList reasons={action.why} />
          </div>
        </div>
      ) : null}
      <div className="mt-5">
        <ButtonLink href={href}>
          {cta} <IconArrowRight />
        </ButtonLink>
      </div>
    </section>
  );
}
