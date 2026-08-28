import Link from "next/link";

import { ProblemsPageContent } from "@/components/problems/ProblemsPageContent";
import { AppShell } from "@/components/ui/AppShell";
import { PageHeader } from "@/components/ui/StatePanels";

export default function ProblemsPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <PageHeader
            eyebrow="Practice"
            title="Practice"
            description="Build evidence through deliberate practice."
          />
          <Link href="/core-cs" className="text-sm font-medium text-accent hover:underline">
            Core CS fundamentals →
          </Link>
        </div>
        <ProblemsPageContent />
      </div>
    </AppShell>
  );
}
