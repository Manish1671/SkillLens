import type { NextRecommendationResponse, RecommendationItem, UserSkillMasteryItem } from "@/lib/api";
import { recommendationFacts } from "@/lib/recommendation-copy";
import { IconCheck, IconX } from "@/components/ui/Icons";
import { ReasonList, SectionLabel } from "@/components/ui/Primitives";

export function WhyRecommendation({
  item,
  targetSkill,
}: {
  item: RecommendationItem;
  targetSkill: UserSkillMasteryItem | null;
}) {
  const facts = recommendationFacts(item, targetSkill);

  return (
    <div data-testid="why-recommendation">
      <SectionLabel>Why SkillLens chose this</SectionLabel>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {facts.map((fact) => (
          <li key={fact.key} className="border-b border-border pb-3">
            <p className="sl-label">{fact.title}</p>
            <p className="mt-1 flex items-center gap-2 text-sm font-medium">
              {fact.ok ? (
                <IconCheck className="h-4 w-4 shrink-0 text-success" />
              ) : (
                <IconX className="h-4 w-4 shrink-0 text-warning" />
              )}
              {fact.value}
            </p>
          </li>
        ))}
      </ul>
      <div className="mt-6">
        <ReasonList reasons={item.explanation.sentences} />
      </div>
    </div>
  );
}

export function WhyFromNextResponse({
  response,
}: {
  response: NextRecommendationResponse | null;
}) {
  if (!response?.recommendation) {
    return (
      <p className="text-sm text-muted">Your first problem is chosen to establish a baseline.</p>
    );
  }
  return (
    <WhyRecommendation item={response.recommendation} targetSkill={response.target_skill} />
  );
}
