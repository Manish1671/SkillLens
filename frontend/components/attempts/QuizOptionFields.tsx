"use client";

import { SectionLabel } from "@/components/ui/Primitives";
import type { QuizOption } from "@/lib/api";

export function QuizOptionFields({
  options,
  selectedOption,
  onSelect,
  disabled = false,
}: {
  options: QuizOption[];
  selectedOption: string | null;
  onSelect: (id: string) => void;
  disabled?: boolean;
}) {
  return (
    <>
      <SectionLabel>Options</SectionLabel>
      <fieldset className="mt-3 space-y-2">
        <legend className="sr-only">Select an answer</legend>
        {options.map((option) => (
          <label
            key={option.id}
            className="flex cursor-pointer items-start gap-3 border border-border bg-surface px-3 py-2 text-sm"
          >
            <input
              type="radio"
              name="quiz-option"
              className="mt-1"
              disabled={disabled}
              checked={selectedOption === option.id}
              onChange={() => onSelect(option.id)}
            />
            <span className="whitespace-pre-wrap">{option.label}</span>
          </label>
        ))}
      </fieldset>
    </>
  );
}
