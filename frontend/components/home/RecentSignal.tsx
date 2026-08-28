import { LearningTimeline } from "@/components/intelligence/LearningTimeline";
import type { AttemptListItem } from "@/lib/api";

export function RecentSignal({ attempts }: { attempts: AttemptListItem[] }) {
  return (
    <section aria-labelledby="recent-signal-heading">
      <h2 id="recent-signal-heading" className="sr-only">
        Recent signal
      </h2>
      <LearningTimeline attempts={attempts} />
    </section>
  );
}
