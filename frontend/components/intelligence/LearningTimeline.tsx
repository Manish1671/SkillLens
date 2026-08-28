import type { AttemptListItem } from "@/lib/api";
import { IconCheck, IconX } from "@/components/ui/Icons";
import { SectionLabel } from "@/components/ui/Primitives";

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  }).toUpperCase();
}

export function LearningTimeline({
  attempts,
}: {
  attempts: AttemptListItem[];
}) {
  const submitted = attempts.filter((item) => item.status === "submitted");

  if (submitted.length === 0) {
    return (
      <div data-testid="learning-timeline">
        <SectionLabel>Recent signal</SectionLabel>
        <p className="mt-3 text-sm text-muted">
          Complete your first problem to create your first evidence point.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="learning-timeline">
      <SectionLabel>Recent evidence</SectionLabel>
      <ol className="mt-3 divide-y divide-border">
        {submitted.slice(0, 8).map((item) => {
          const positive = item.is_correct === true;
          const isQuiz = item.problem.activity_kind === "quiz";
          return (
            <li key={item.id} className="flex items-start gap-3 py-3">
              <span className="w-16 shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted">
                {formatDay(item.submitted_at ?? item.started_at)}
              </span>
              <span
                className={`mt-0.5 ${positive ? "text-success" : "text-danger"}`}
                aria-hidden
              >
                {positive ? <IconCheck className="h-4 w-4" /> : <IconX className="h-4 w-4" />}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {isQuiz
                    ? positive
                      ? `Quiz completed · ${item.problem.title}`
                      : `Missed quiz · ${item.problem.title}`
                    : `${positive ? "Solved" : "Failed"} ${item.problem.title}`}
                </p>
                <p className="text-xs text-muted">
                  {isQuiz
                    ? "Core CS signal"
                    : positive
                      ? "DSA signal"
                      : "Negative evidence"}
                  {item.hints_used_count > 0 ? ` · ${item.hints_used_count} hint(s)` : ""}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
