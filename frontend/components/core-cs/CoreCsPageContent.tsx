"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DifficultyBadge } from "@/components/problems/ProblemBadges";
import { SectionLabel } from "@/components/ui/Primitives";
import { ErrorState, LoadingState, PageHeader } from "@/components/ui/StatePanels";
import {
  getCurrentUser,
  getMyMastery,
  listProblems,
  listSkills,
  type ProblemListItem,
  type SkillSummary,
  type UserSkillMasteryItem,
} from "@/lib/api";
import { CORE_CS_TOPIC_SLUG, confidenceLabel, mergeSkillProfile, scoreValue } from "@/lib/catalog-ui";

const CORE_SKILL_ORDER = [
  "sql-basics",
  "sql-joins",
  "normalization",
  "indexing",
  "transactions",
];

export function CoreCsPageContent() {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [quizzes, setQuizzes] = useState<ProblemListItem[]>([]);
  const [mastery, setMastery] = useState<UserSkillMasteryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const [skillsResult, quizzesResult, userResult] = await Promise.all([
        listSkills(),
        listProblems({ topic: CORE_CS_TOPIC_SLUG, activity_kind: "quiz", limit: 50 }),
        getCurrentUser(),
      ]);
      if (skillsResult.error || quizzesResult.error) {
        setError("Could not load Core CS content.");
        setLoading(false);
        return;
      }
      const coreSkills = (skillsResult.data ?? []).filter(
        (skill) => skill.topic_slug === CORE_CS_TOPIC_SLUG
      );
      setSkills(coreSkills);
      setQuizzes(quizzesResult.data?.items ?? []);
      if (userResult.data) {
        const masteryResult = await getMyMastery();
        setMastery(mergeSkillProfile(coreSkills, masteryResult.data?.items ?? []));
      } else {
        setMastery(mergeSkillProfile(coreSkills, []));
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return <LoadingState message="Loading Core CS..." />;
  }
  if (error) {
    return <ErrorState message={error} />;
  }

  const assessed = mastery.filter((item) => item.status === "assessed" && item.score !== null).length;
  const orderedSkills = [...skills].sort(
    (a, b) => CORE_SKILL_ORDER.indexOf(a.slug) - CORE_SKILL_ORDER.indexOf(b.slug)
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Core CS"
        title="Core CS"
        description="Measure the fundamentals behind your engineering decisions."
      />

      <section className="border-y border-border py-4">
        <SectionLabel>Assessment state</SectionLabel>
        {assessed === 0 ? (
          <p className="mt-2 text-sm text-muted">Core CS hasn&apos;t been assessed yet.</p>
        ) : (
          <p className="mt-2 sl-num text-lg font-semibold">
            {assessed} / {orderedSkills.length} skills assessed
          </p>
        )}
        <p className="mt-1 text-sm text-muted">
          A Core CS score appears only after enough skills have real evidence — insufficient is not 0%.
        </p>
      </section>

      <section>
        <SectionLabel>Skills</SectionLabel>
        <div className="mt-3 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
          {orderedSkills.map((skill) => {
            const item = mastery.find((row) => row.skill_slug === skill.slug);
            const score = scoreValue(item?.score ?? null);
            const assessedSkill = item?.status === "assessed" && score !== null;
            return (
              <Link
                key={skill.slug}
                href={`/skills/${skill.slug}`}
                className="block border-b border-border py-3 hover:bg-white"
              >
                <p className="font-semibold">{skill.name}</p>
                <p className="mt-2 text-sm text-muted">
                  {assessedSkill
                    ? `${Math.round((score ?? 0) * 100)}% · ${confidenceLabel(item?.confidence ?? "0")}`
                    : "Not enough evidence yet"}
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      <section>
        <SectionLabel>Quizzes</SectionLabel>
        <div className="mt-3 border-t border-border">
          {quizzes.map((quiz) => (
            <Link
              key={quiz.id}
              href={`/problems/${quiz.slug}`}
              className="flex items-center justify-between gap-3 border-b border-border px-2 py-3 hover:bg-white"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{quiz.title}</p>
                <p className="text-xs text-muted">
                  {quiz.skills.find((skill) => skill.is_primary)?.name ?? "DBMS"}
                </p>
              </div>
              <DifficultyBadge difficulty={quiz.difficulty} />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
