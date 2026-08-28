"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import {
  listProblems,
  listSkills,
  listTopics,
  type ProblemListItem,
  type SkillSummary,
  type TopicSummary,
} from "@/lib/api";

import {
  ProblemFilters,
  ProblemListSection,
  type ProblemFilterValues,
} from "./ProblemList";

const EMPTY_FILTERS: ProblemFilterValues = {
  q: "",
  topic: "",
  skill: "",
  difficulty: "",
  activity: "all",
};

export function ProblemsPageContent() {
  const [topics, setTopics] = useState<TopicSummary[]>([]);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [filters, setFilters] = useState<ProblemFilterValues>(EMPTY_FILTERS);
  const [debouncedQ, setDebouncedQ] = useState("");
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);

  useEffect(() => {
    async function loadMeta() {
      const [topicsResult, skillsResult] = await Promise.all([listTopics(), listSkills()]);
      if (topicsResult.error || skillsResult.error) {
        setMetaError("Could not load catalog filters.");
        return;
      }
      setTopics(topicsResult.data ?? []);
      setSkills(skillsResult.data ?? []);
    }

    loadMeta();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(filters.q), 300);
    return () => window.clearTimeout(timer);
  }, [filters.q]);

  useEffect(() => {
    async function loadProblems() {
      setLoading(true);
      setError(null);

      const result = await listProblems({
        topic: filters.topic || undefined,
        skill: filters.skill || undefined,
        difficulty: filters.difficulty
          ? (filters.difficulty as "easy" | "medium" | "hard")
          : undefined,
        activity_kind: filters.activity === "all" ? undefined : filters.activity,
        q: debouncedQ || undefined,
        limit: 20,
      });

      if (result.error) {
        setError(result.error.detail);
        setLoading(false);
        return;
      }

      const data = result.data;
      if (!data) {
        setError("No data returned.");
        setLoading(false);
        return;
      }

      setProblems(data.items);
      setCursor(data.next_cursor);
      setHasMore(data.has_more);
      setLoading(false);
    }

    loadProblems();
  }, [debouncedQ, filters.activity, filters.difficulty, filters.skill, filters.topic]);

  const loadMore = async () => {
    if (!hasMore || loadingMore) {
      return;
    }

    setLoadingMore(true);
    const result = await listProblems({
      topic: filters.topic || undefined,
      skill: filters.skill || undefined,
      difficulty: filters.difficulty
        ? (filters.difficulty as "easy" | "medium" | "hard")
        : undefined,
      activity_kind: filters.activity === "all" ? undefined : filters.activity,
      q: debouncedQ || undefined,
      cursor: cursor ?? undefined,
      limit: 20,
    });

    if (result.error) {
      setError(result.error.detail);
      setLoadingMore(false);
      return;
    }

    const data = result.data;
    if (!data) {
      setError("No data returned.");
      setLoadingMore(false);
      return;
    }

    setProblems((current) => [...current, ...data.items]);
    setCursor(data.next_cursor);
    setHasMore(data.has_more);
    setLoadingMore(false);
  };

  return (
    <div className="space-y-6">
      {metaError ? (
        <p className="text-sm text-warning">{metaError}</p>
      ) : (
        <ProblemFilters
          topics={topics}
          skills={skills}
          values={filters}
          onChange={setFilters}
        />
      )}

      <ProblemListSection
        loading={loading}
        error={error}
        problems={problems}
        emptyMessage="No problems match your filters."
      />

      {hasMore && !loading && !error ? (
        <Button
          variant="secondary"
          className="w-full"
          disabled={loadingMore}
          onClick={() => loadMore()}
        >
          {loadingMore ? "Loading..." : "Load more"}
        </Button>
      ) : null}
    </div>
  );
}
