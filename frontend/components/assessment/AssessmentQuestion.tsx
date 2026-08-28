"use client";

import { FormEvent } from "react";

import { AssessmentProgress } from "@/components/assessment/AssessmentProgress";
import { QuizOptionFields } from "@/components/attempts/QuizOptionFields";
import { DifficultyBadge } from "@/components/problems/ProblemBadges";
import { Button } from "@/components/ui/Button";
import type { ProblemDetail } from "@/lib/api";

export function AssessmentQuestion({
  problem,
  index,
  total,
  dimension,
  error,
  submitting,
  isQuiz,
  isCorrect,
  selectedOption,
  onCorrectChange,
  onSelectOption,
  onSubmit,
}: {
  problem: ProblemDetail;
  index: number;
  total: number;
  dimension: string;
  error: string | null;
  submitting: boolean;
  isQuiz: boolean;
  isCorrect: boolean | null;
  selectedOption: string | null;
  onCorrectChange: (value: boolean) => void;
  onSelectOption: (id: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const canSubmit = isQuiz ? selectedOption !== null : isCorrect !== null;
  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="assessment-question">
      <AssessmentProgress current={index + 1} total={total} dimension={dimension} />
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{problem.title}</h1>
        <div className="mt-2 flex flex-wrap gap-2 text-sm text-muted">
          <DifficultyBadge difficulty={problem.difficulty} />
          <span>{problem.estimated_minutes} min</span>
        </div>
      </div>
      <div className="border border-border bg-surface p-5 text-sm leading-relaxed whitespace-pre-wrap">
        {problem.prompt_md}
      </div>
      {error ? (
        <p className="text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}
      <form onSubmit={onSubmit} className="space-y-4">
        {isQuiz ? (
          <QuizOptionFields
            options={problem.options ?? []}
            selectedOption={selectedOption}
            onSelect={onSelectOption}
            disabled={submitting}
          />
        ) : (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">How did this go?</legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="outcome"
                checked={isCorrect === true}
                onChange={() => onCorrectChange(true)}
              />
              I would solve this correctly
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="outcome"
                checked={isCorrect === false}
                onChange={() => onCorrectChange(false)}
              />
              I would not solve this correctly
            </label>
          </fieldset>
        )}
        <Button type="submit" disabled={submitting || !canSubmit}>
          Submit
        </Button>
      </form>
    </div>
  );
}
