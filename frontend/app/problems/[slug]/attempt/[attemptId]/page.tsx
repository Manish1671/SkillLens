import { AttemptPageContent } from "@/components/attempts/AttemptPageContent";
import { AppShell } from "@/components/ui/AppShell";

type AttemptPageProps = {
  params: Promise<{ slug: string; attemptId: string }>;
};

export default async function AttemptPage({ params }: AttemptPageProps) {
  const { slug, attemptId } = await params;
  return (
    <AppShell>
      <AttemptPageContent slug={slug} attemptId={attemptId} />
    </AppShell>
  );
}
