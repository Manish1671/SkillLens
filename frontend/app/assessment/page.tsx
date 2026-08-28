import { Suspense } from "react";

import { AssessmentFlow } from "@/components/assessment/AssessmentFlow";
import { AppShell } from "@/components/ui/AppShell";
import { LoadingState } from "@/components/ui/StatePanels";

export default function AssessmentPage() {
  return (
    <AppShell>
      <Suspense fallback={<LoadingState message="Loading assessment..." />}>
        <AssessmentFlow />
      </Suspense>
    </AppShell>
  );
}
