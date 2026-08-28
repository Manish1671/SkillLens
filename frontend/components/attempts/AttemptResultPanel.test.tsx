import { render, screen } from "@testing-library/react";

import { describe, expect, it } from "vitest";



import { AttemptResultPanel } from "./AttemptResultPanel";



describe("AttemptResultPanel", () => {

  it("renders result, mastery movement, evidence, and recommendation", () => {

    render(

      <AttemptResultPanel

        isCorrect={true}

        assessment={{

          evidence_items: [

            {

              id: "e1",

              evidence_type: "solved_without_hints",

              polarity: "positive",

              strength: "0.7200",

              summary_text: "Solved without hints — primary skill Hashing.",

              skill_slug: "hashing",

              skill_name: "Hashing",

              created_at: "2026-01-01T00:00:00Z",

            },

          ],

          mastery_deltas: [

            {

              skill_slug: "hashing",

              skill_name: "Hashing",

              previous_score: null,

              new_score: "0.4200",

              delta: "0.4200",

              status: "assessed",

              confidence: "0.3500",

              prerequisite_capped: false,

            },

          ],

          recommendation: {

            state: "ok",

            message: null,

            target_skill: {

              skill_slug: "hashing",

              skill_name: "Hashing",

              topic_slug: "arrays-and-hashing",

              score: "0.4200",

              confidence: "0.3500",

              status: "assessed",

              evidence_count: 1,

              last_attempt_at: "2026-01-01T00:00:00Z",

            },

            recommendation: {

              id: "rec-1",

              rank: 1,

              score: "0.8100",

              generated_at: "2026-01-01T00:00:00Z",

              source_attempt_id: "attempt-1",

              problem: {

                id: "p1",

                slug: "contains-duplicate",

                title: "Contains Duplicate",

                difficulty: "easy",

                estimated_minutes: 15,

                skills: [],

                target_skill: {

                  slug: "hashing",

                  name: "Hashing",

                  weight: "1.0",

                  is_primary: true,

                },

              },

              explanation: {

                target_skill: "hashing",

                reason_codes: ["weak_skill", "novel_problem"],

                score_components: { final_score: 0.81 },

                sentences: [

                  "Your Hashing skill is currently one of your weaker assessed skills.",

                  "You have not solved this problem before.",

                ],

              },

            },

          },

        }}

      />

    );



    expect(screen.getByText("Problem solved")).toBeInTheDocument();

    expect(screen.getByText("Skill impact")).toBeInTheDocument();

    expect(screen.getByText(/Solved without hints/)).toBeInTheDocument();

    expect(screen.getByText("Contains Duplicate")).toBeInTheDocument();

    expect(screen.getByText("Start next problem")).toBeInTheDocument();

  });

  it("renders quiz result with core cs readiness copy", () => {
    render(
      <AttemptResultPanel
        isCorrect={true}
        activityKind="quiz"
        assessment={{
          evidence_items: [
            {
              id: "e1",
              evidence_type: "solved_without_hints",
              polarity: "positive",
              strength: "0.7200",
              summary_text: "Correct answer — primary skill SQL Joins.",
              skill_slug: "sql-joins",
              skill_name: "SQL Joins",
              created_at: "2026-01-01T00:00:00Z",
            },
          ],
          mastery_deltas: [
            {
              skill_slug: "sql-joins",
              skill_name: "SQL Joins",
              previous_score: null,
              new_score: "0.4200",
              delta: "0.4200",
              status: "assessed",
              confidence: "0.3500",
              prerequisite_capped: false,
            },
          ],
          recommendation: null,
        }}
        readiness={{
          target: {
            slug: "product-sde",
            name: "Product SDE",
            description: "",
            disclaimer: "",
          },
          state: "developing",
          confidence: 0.4,
          risk: "high",
          dimensions: [
            {
              key: "core_cs",
              display_name: "Core CS",
              status: "developing",
              score: 0.47,
              confidence: 0.4,
              coverage: 0.8,
              assessed_count: 4,
              in_scope_count: 5,
            },
          ],
          blockers: [
            {
              dimension: "core_cs",
              skill_slug: null,
              skill_name: null,
              current: 0.47,
              required: 0.6,
              delta: -0.13,
              status: "below",
              severity: "critical_blocker",
              why: "Core CS is at 47% versus the 60% target bar.",
              rank: 1,
            },
          ],
          score: null,
          disclaimer: "",
        }}
      />
    );

    expect(screen.getByText("Correct answer")).toBeInTheDocument();
    expect(screen.getByText("Core CS signal")).toBeInTheDocument();
    expect(screen.getByText("Core CS is at 47% versus the 60% target bar.")).toBeInTheDocument();
  });



  it("shows insufficient mastery without fake percentage", () => {

    render(

      <AttemptResultPanel

        isCorrect={false}

        assessment={{

          evidence_items: [],

          mastery_deltas: [

            {

              skill_slug: "hashing",

              skill_name: "Hashing",

              previous_score: null,

              new_score: null,

              delta: null,

              status: "insufficient",

              confidence: "0.1000",

              prerequisite_capped: false,

            },

          ],

          recommendation: null,

        }}

      />

    );



    expect(screen.getByText("Not quite")).toBeInTheDocument();

    expect(screen.getByText(/Gathering evidence/)).toBeInTheDocument();

  });

});

