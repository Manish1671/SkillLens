import { getSkill, listSkills, type SkillSummary } from "@/lib/api";

export type CatalogGraph = {
  skills: SkillSummary[];
  edges: { from: string; to: string }[];
};

export async function loadCatalogGraph(): Promise<CatalogGraph> {
  const skillsResult = await listSkills();
  const skills = skillsResult.data ?? [];
  const withPrereqs = skills.filter((skill) => skill.prerequisite_skill_ids.length > 0);
  const details = await Promise.all(withPrereqs.map((skill) => getSkill(skill.slug)));
  const edges = details.flatMap((result) =>
    (result.data?.prerequisites ?? []).map((prereq) => ({
      from: prereq.slug,
      to: result.data!.slug,
    }))
  );
  return { skills, edges };
}
