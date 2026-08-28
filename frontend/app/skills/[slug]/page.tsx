import { AppShell } from "@/components/ui/AppShell";

import { SkillDetailPageContent } from "@/components/skills/SkillDetailPageContent";

type SkillPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function SkillPage({ params }: SkillPageProps) {
  const { slug } = await params;
  return (
    <AppShell>
      <SkillDetailPageContent slug={slug} />
    </AppShell>
  );
}
