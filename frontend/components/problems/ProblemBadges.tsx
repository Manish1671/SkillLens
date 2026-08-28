import type { ProblemSkillLink } from "@/lib/api";
import { difficultyClasses, difficultyLabel } from "@/lib/catalog-ui";

export function DifficultyBadge({
  difficulty,
}: {
  difficulty: "easy" | "medium" | "hard";
}) {
  return (
    <span className={`inline-flex px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${difficultyClasses(difficulty)}`}>
      {difficultyLabel(difficulty)}
    </span>
  );
}

export function SkillBadges({ skills }: { skills: ProblemSkillLink[] }) {
  if (skills.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <span
          key={skill.slug}
          className={`px-1.5 py-0.5 text-[11px] font-medium ${
            skill.is_primary ? "bg-ink text-white" : "bg-surface-muted text-muted"
          }`}
        >
          {skill.name}
        </span>
      ))}
    </div>
  );
}
