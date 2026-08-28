import Link from "next/link";

import { IconArrowRight, IconSearch } from "@/components/ui/Icons";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StatePanels";
import type { ProblemListItem, SkillSummary, TopicSummary } from "@/lib/api";
import { DIFFICULTY_OPTIONS, formatMinutes } from "@/lib/catalog-ui";

import { DifficultyBadge } from "./ProblemBadges";

export type ProblemFilterValues = {
  q: string;
  topic: string;
  skill: string;
  difficulty: string;
  activity: "all" | "coding" | "quiz";
};

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active ? "bg-ink text-white" : "bg-surface-muted text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

export function ProblemFilters({
  topics,
  skills,
  values,
  onChange,
}: {
  topics: TopicSummary[];
  skills: SkillSummary[];
  values: ProblemFilterValues;
  onChange: (values: ProblemFilterValues) => void;
}) {
  const topicSkills = values.topic
    ? skills.filter((skill) => skill.topic_slug === values.topic)
    : skills;

  return (
    <div className="space-y-4">
      <label className="relative block">
        <span className="sr-only">Search</span>
        <span className="pointer-events-none absolute left-3 top-2.5 text-muted">
          <IconSearch />
        </span>
        <input
          type="search"
          placeholder="Search problems..."
          className="sl-input pl-9"
          value={values.q}
          onChange={(event) => onChange({ ...values, q: event.target.value })}
        />
      </label>

      <div className="flex flex-wrap gap-1.5">
        {(
          [
            ["all", "All"],
            ["coding", "Coding"],
            ["quiz", "Quiz"],
          ] as const
        ).map(([value, label]) => (
          <FilterPill
            key={value}
            active={values.activity === value}
            onClick={() => onChange({ ...values, activity: value })}
          >
            {label}
          </FilterPill>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        <FilterPill active={!values.topic} onClick={() => onChange({ ...values, topic: "", skill: "" })}>
          All
        </FilterPill>
        {topics.map((topic) => (
          <FilterPill
            key={topic.slug}
            active={values.topic === topic.slug}
            onClick={() =>
              onChange({
                ...values,
                topic: values.topic === topic.slug ? "" : topic.slug,
                skill: "",
              })
            }
          >
            {topic.name}
          </FilterPill>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        <FilterPill active={!values.skill} onClick={() => onChange({ ...values, skill: "" })}>
          All skills
        </FilterPill>
        {topicSkills.map((skill) => (
          <FilterPill
            key={skill.slug}
            active={values.skill === skill.slug}
            onClick={() =>
              onChange({
                ...values,
                skill: values.skill === skill.slug ? "" : skill.slug,
              })
            }
          >
            {skill.name}
          </FilterPill>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {DIFFICULTY_OPTIONS.map((option) => (
          <FilterPill
            key={option.value}
            active={values.difficulty === option.value}
            onClick={() => onChange({ ...values, difficulty: option.value })}
          >
            {option.label}
          </FilterPill>
        ))}
      </div>
    </div>
  );
}

function LearnerState({ problem }: { problem: ProblemListItem }) {
  if (problem.learner_state?.solved) {
    return <span className="text-xs font-semibold text-success">Solved</span>;
  }
  if (problem.learner_state?.in_progress) {
    return <span className="text-xs font-semibold text-warning">Resume</span>;
  }
  return <span className="text-xs font-semibold text-accent">Start</span>;
}

export function ProblemCard({ problem, index }: { problem: ProblemListItem; index?: number }) {
  const primary = problem.skills.find((s) => s.is_primary);
  return (
    <Link
      href={`/problems/${problem.slug}`}
      className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border-b border-border px-2 py-3 transition-colors hover:bg-white sm:grid-cols-[2.75rem_minmax(0,1fr)_4rem_5.5rem_4.5rem_4.5rem]"
    >
      <span className="font-mono text-xs text-muted-light">
        #{String((index ?? 0) + 1).padStart(2, "0")}
      </span>
      <div className="min-w-0">
        <p className="truncate font-medium group-hover:text-accent">{problem.title}</p>
        <p className="mt-0.5 truncate text-xs text-muted">
          {problem.activity_kind === "quiz" ? "Quiz · " : ""}
          {primary?.name ?? problem.topic.name}
        </p>
      </div>
      <span className="hidden text-xs uppercase tracking-wide text-muted sm:block">
        {problem.activity_kind === "quiz" ? "Quiz" : "Coding"}
      </span>
      <span className="hidden sm:block">
        <DifficultyBadge difficulty={problem.difficulty} />
      </span>
      <span className="hidden text-sm text-muted sm:block">{formatMinutes(problem.estimated_minutes)}</span>
      <span className="flex items-center justify-end gap-2">
        <LearnerState problem={problem} />
        <IconArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
      </span>
    </Link>
  );
}

export function ProblemListSection({
  loading,
  error,
  problems,
  emptyMessage,
}: {
  loading: boolean;
  error: string | null;
  problems: ProblemListItem[];
  emptyMessage: string;
}) {
  if (loading) {
    return <LoadingState message="Loading problems..." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (problems.length === 0) {
    return <EmptyState title="No problems found" description={emptyMessage} />;
  }

  return (
    <div className="border-t border-border">
      <div className="hidden grid-cols-[2.75rem_minmax(0,1fr)_4rem_5.5rem_4.5rem_4.5rem] gap-3 px-2 py-2 text-[11px] uppercase tracking-[0.12em] text-muted sm:grid">
        <span>#</span>
        <span>Problem</span>
        <span>Type</span>
        <span>Difficulty</span>
        <span>Time</span>
        <span className="text-right">State</span>
      </div>
      {problems.map((problem, index) => (
        <ProblemCard key={problem.id} problem={problem} index={index} />
      ))}
    </div>
  );
}
