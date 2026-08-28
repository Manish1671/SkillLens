import { ProblemDetailView } from "@/components/problems/ProblemDetailView";
import { AppShell } from "@/components/ui/AppShell";

type ProblemPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function ProblemPage({ params }: ProblemPageProps) {
  const { slug } = await params;
  return (
    <AppShell>
      <ProblemDetailView slug={slug} />
    </AppShell>
  );
}
