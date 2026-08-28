import { LogoMark } from "@/components/brand/Logo";
import { ButtonLink } from "@/components/ui/Button";
import { IconArrowRight } from "@/components/ui/Icons";
import { ReasonList, SectionLabel } from "@/components/ui/Primitives";
import { SkillMap } from "@/components/skills/SkillMap";

const DEMO_NODES = [
  { slug: "arrays", name: "Arrays", score: "0.87", status: "assessed" },
  { slug: "hashing", name: "Hashing", score: "0.79", status: "assessed" },
  { slug: "two-pointers", name: "Two Pointers", score: "0.78", status: "assessed" },
  { slug: "sliding-window", name: "Sliding Window", score: "0.46", status: "assessed" },
];
const DEMO_EDGES = [
  { from: "arrays", to: "hashing" },
  { from: "arrays", to: "two-pointers" },
  { from: "two-pointers", to: "sliding-window" },
];

function LoopStep({ n, label }: { n: string; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="font-mono text-[11px] text-accent">{n}</span>
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

export function LandingPage() {
  return (
    <div>
      <section className="sl-container grid items-end gap-10 py-10 lg:grid-cols-12 lg:py-14">
        <div className="lg:col-span-7">
          <div className="mb-5 text-accent">
            <LogoMark className="h-9 w-9" />
          </div>
          <p className="sl-page-kicker">Placement readiness intelligence</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-[2.75rem]">
            Know what you actually understand.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-relaxed text-muted">
            SkillLens reconstructs your placement readiness from evidence — then tells you what is blocking the
            target, and why the next action is the highest priority.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <ButtonLink href="/assessment" size="lg">
              Assess Me <IconArrowRight />
            </ButtonLink>
            <ButtonLink href="/register" variant="secondary" size="lg">
              Get started
            </ButtonLink>
          </div>
        </div>
        <div className="lg:col-span-5">
          <p className="sl-label">Signal → interpretation → action</p>
          <div className="mt-4 space-y-4 border-t border-border pt-4">
            <div>
              <p className="text-sm text-muted">Core CS</p>
              <p className="sl-num text-3xl font-semibold">52%</p>
            </div>
            <p className="text-sm">Below Product SDE target</p>
            <p className="text-sm font-medium text-warning">Critical blocker</p>
            <p className="text-sm text-accent">Next: Assess Transactions</p>
            <p className="text-[11px] uppercase tracking-wider text-muted">Illustrative</p>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-surface">
        <div className="sl-container grid gap-8 py-10 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <h2 className="text-2xl font-semibold tracking-tight">This is not a scoreboard.</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              SkillLens does not count problems finished. It observes evidence, interprets readiness against a
              target, and ranks the next action.
            </p>
          </div>
          <div className="grid gap-8 text-sm lg:col-span-7 sm:grid-cols-2">
            <div>
              <p className="sl-label">Where am I?</p>
              <p className="mt-3 leading-relaxed text-muted">
                State, confidence, and which dimensions have enough evidence to speak.
              </p>
            </div>
            <div>
              <p className="sl-label">What should I do?</p>
              <p className="mt-3 leading-relaxed text-muted">
                One ranked placement action, with deterministic reasons — not a feed of problems.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="sl-container py-10">
        <SectionLabel>The loop</SectionLabel>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Observe. Assess. Act. Reassess.</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <LoopStep n="01" label="Observe" />
          <LoopStep n="02" label="Assess" />
          <LoopStep n="03" label="Understand" />
          <LoopStep n="04" label="Identify gaps" />
          <LoopStep n="05" label="Act" />
          <LoopStep n="06" label="Reassess" />
        </div>
      </section>

      <section className="sl-container grid gap-10 py-10 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <h2 className="text-2xl font-semibold tracking-tight">Every next move has a reason.</h2>
          <p className="mt-3 text-sm text-muted">The highest-priority action is inspectable, not opaque.</p>
        </div>
        <div className="lg:col-span-7">
          <p className="sl-label">Your next move</p>
          <h3 className="mt-2 text-xl font-semibold">Improve SQL Transactions</h3>
          <div className="mt-5">
            <ReasonList
              reasons={[
                "Core CS is a critical target requirement.",
                "Current evidence is below target.",
                "Transactions is one of the weakest actionable skills.",
              ]}
            />
          </div>
        </div>
      </section>

      <section className="sl-container py-10">
        <SectionLabel>Illustrative map</SectionLabel>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Skills as a system, not a list.</h2>
        <div className="mt-5">
          <SkillMap nodes={DEMO_NODES} edges={DEMO_EDGES} focusSlug="sliding-window" compact />
        </div>
      </section>

      <section className="border-t border-border">
        <div className="sl-container flex flex-wrap items-end justify-between gap-6 py-12">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Start with a baseline, not a guess.</h2>
            <p className="mt-2 text-sm text-muted">Your skill model begins with the first assessment.</p>
          </div>
          <ButtonLink href="/register" size="lg">
            Build your skill profile <IconArrowRight />
          </ButtonLink>
        </div>
      </section>
    </div>
  );
}
