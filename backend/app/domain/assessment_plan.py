"""Pure placement diagnostic planning — no framework or database imports.

This layer only chooses a small, deterministic mixture of published DSA problems
and Core CS quizzes. Attempt, evidence, mastery, and readiness stay elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from app.core.enums import (
    ActivityKind,
    Difficulty,
    DimensionStatus,
    MasteryStatus,
    ReadinessDimension,
)

# Canonical representative skills (backend source of truth — not the frontend).
DSA_DIAGNOSTIC_SKILLS: tuple[str, ...] = (
    "arrays",
    "hashing",
    "two-pointers",
    "binary-search",
    "linked-lists",
    "stack",
    "trees",
    "graphs",
    "sliding-window",
    "dynamic-programming",
)

CORE_CS_DIAGNOSTIC_SKILLS: tuple[str, ...] = (
    "sql-basics",
    "sql-joins",
    "normalization",
    "indexing",
    "transactions",
)

DEFAULT_DSA_SLOTS = 7
DEFAULT_CS_SLOTS = 4
MIN_TOTAL_ITEMS = 10
MAX_TOTAL_ITEMS = 12

STRONG_SCORE = 0.75
STRONG_EVIDENCE = 3
STRONG_COVERAGE = 0.40
WEAK_SCORE = 0.55
TARGET_MEET_SCORE = 0.60

NEED_INSUFFICIENT = 1.0
NEED_WEAK = 0.90
NEED_DEVELOPING = 0.45
NEED_STRONG = 0.12

DIFFICULTY_RANK: dict[Difficulty, int] = {
    Difficulty.EASY: 0,
    Difficulty.MEDIUM: 1,
    Difficulty.HARD: 2,
}
DIFFICULTY_CYCLE: tuple[Difficulty, ...] = (
    Difficulty.EASY,
    Difficulty.MEDIUM,
    Difficulty.HARD,
)

PRIMARY_WEIGHT_THRESHOLD = 1.0


@dataclass(frozen=True)
class PlanSkillInput:
    slug: str
    name: str
    dimension: ReadinessDimension
    is_foundational: bool
    sort_order: int
    prerequisite_slugs: tuple[str, ...]
    score: float | None
    confidence: float
    status: MasteryStatus
    evidence_count: int


@dataclass(frozen=True)
class PlanProblemInput:
    problem_id: str
    slug: str
    title: str
    activity_kind: ActivityKind
    difficulty: Difficulty
    estimated_minutes: int
    skill_slugs: tuple[str, ...]
    primary_skill_slug: str | None
    skill_weights: tuple[tuple[str, float], ...]
    is_published: bool
    attempted: bool
    solved: bool
    in_progress: bool


@dataclass(frozen=True)
class PlanDimensionInput:
    key: ReadinessDimension
    status: DimensionStatus
    score: float | None
    coverage: float
    assessed_count: int


@dataclass(frozen=True)
class PlanTargetInput:
    slug: str
    name: str
    dsa_weight: float
    core_cs_weight: float


@dataclass(frozen=True)
class AssessmentPlanItem:
    position: int
    activity_kind: ActivityKind
    problem_id: str
    problem_slug: str
    problem_title: str
    dimension: ReadinessDimension
    skill_slug: str
    skill_name: str
    estimated_minutes: int
    difficulty: Difficulty


@dataclass(frozen=True)
class AssessmentPlan:
    assessment_id: str
    target_slug: str
    target_name: str
    items: tuple[AssessmentPlanItem, ...]
    dsa_slots: int
    cs_slots: int

    @property
    def total_items(self) -> int:
        return len(self.items)


def skill_need(skill: PlanSkillInput) -> float:
    """Higher need → earlier diagnostic priority. Weak skills stay represented."""
    if skill.status != MasteryStatus.ASSESSED or skill.evidence_count <= 0:
        return NEED_INSUFFICIENT
    if skill.score is None:
        return NEED_INSUFFICIENT
    if skill.score < WEAK_SCORE:
        return NEED_WEAK
    if skill.score >= STRONG_SCORE and skill.evidence_count >= STRONG_EVIDENCE:
        return NEED_STRONG
    return NEED_DEVELOPING


def dimension_is_strong(item: PlanDimensionInput | None) -> bool:
    if item is None:
        return False
    if item.status in {DimensionStatus.NOT_ASSESSED, DimensionStatus.EARLY}:
        return False
    if item.score is None or item.coverage < STRONG_COVERAGE:
        return False
    return item.score >= STRONG_SCORE and item.assessed_count >= STRONG_EVIDENCE


def dimension_needs_focus(item: PlanDimensionInput | None) -> bool:
    if item is None:
        return True
    if item.status == DimensionStatus.NOT_ASSESSED:
        return True
    if item.coverage < STRONG_COVERAGE or item.score is None:
        return True
    return item.score < TARGET_MEET_SCORE


def allocate_slots(
    dsa: PlanDimensionInput | None,
    core_cs: PlanDimensionInput | None,
    target: PlanTargetInput,
    bias_dimension: ReadinessDimension | None = None,
) -> tuple[int, int]:
    """Return (dsa_slots, cs_slots) in [10, 12], biased toward weaker / heavier dimensions."""
    dsa_n = DEFAULT_DSA_SLOTS
    cs_n = DEFAULT_CS_SLOTS
    dsa_strong = dimension_is_strong(dsa)
    cs_strong = dimension_is_strong(core_cs)
    dsa_focus = dimension_needs_focus(dsa)
    cs_focus = dimension_needs_focus(core_cs)

    if dsa_strong and cs_focus:
        dsa_n, cs_n = 6, 5
    elif cs_strong and dsa_focus:
        dsa_n, cs_n = 8, 4
    elif dsa_strong and cs_strong:
        dsa_n, cs_n = 6, 4
    elif target.core_cs_weight > target.dsa_weight + 0.049:
        dsa_n, cs_n = 6, 5

    if bias_dimension == ReadinessDimension.CORE_CS and dsa_n > 6:
        dsa_n -= 1
        cs_n += 1
    elif bias_dimension == ReadinessDimension.DSA and cs_n > 4:
        cs_n -= 1
        dsa_n += 1

    total = dsa_n + cs_n
    if total < MIN_TOTAL_ITEMS:
        dsa_n += MIN_TOTAL_ITEMS - total
    if dsa_n + cs_n > MAX_TOTAL_ITEMS:
        overflow = dsa_n + cs_n - MAX_TOTAL_ITEMS
        if dsa_n >= cs_n:
            dsa_n -= overflow
        else:
            cs_n -= overflow
    return dsa_n, cs_n


def _canonical_index(slug: str, dimension: ReadinessDimension) -> int:
    table = (
        CORE_CS_DIAGNOSTIC_SKILLS
        if dimension == ReadinessDimension.CORE_CS
        else DSA_DIAGNOSTIC_SKILLS
    )
    try:
        return table.index(slug)
    except ValueError:
        return 1000 + (0 if slug else 1)


def rank_skills(skills: list[PlanSkillInput]) -> list[PlanSkillInput]:
    return sorted(
        skills,
        key=lambda skill: (
            -skill_need(skill),
            _canonical_index(skill.slug, skill.dimension),
            0 if skill.is_foundational else 1,
            skill.sort_order,
            skill.slug,
        ),
    )


def _problem_covers_skill(problem: PlanProblemInput, skill_slug: str) -> bool:
    if problem.primary_skill_slug == skill_slug:
        return True
    return skill_slug in problem.skill_slugs


def pick_problem_for_skill(
    skill: PlanSkillInput,
    problems: list[PlanProblemInput],
    used_ids: set[str],
    slot_index: int,
) -> PlanProblemInput | None:
    expected_kind = (
        ActivityKind.QUIZ if skill.dimension == ReadinessDimension.CORE_CS else ActivityKind.CODING
    )
    prefer = DIFFICULTY_CYCLE[slot_index % len(DIFFICULTY_CYCLE)]
    prefer_rank = DIFFICULTY_RANK[prefer]
    eligible = [
        problem
        for problem in problems
        if problem.is_published
        and not problem.in_progress
        and problem.problem_id not in used_ids
        and problem.activity_kind == expected_kind
        and _problem_covers_skill(problem, skill.slug)
    ]
    if not eligible:
        return None

    def sort_key(problem: PlanProblemInput) -> tuple:
        primary = 0 if problem.primary_skill_slug == skill.slug else 1
        solved_penalty = 1 if problem.solved else 0
        diff_rank = DIFFICULTY_RANK[problem.difficulty]
        return (
            primary,
            solved_penalty,
            abs(diff_rank - prefer_rank),
            diff_rank,
            problem.slug,
        )

    return sorted(eligible, key=sort_key)[0]


def _fill_dimension(
    skills: list[PlanSkillInput],
    problems: list[PlanProblemInput],
    slots: int,
    used_ids: set[str],
) -> list[tuple[PlanSkillInput, PlanProblemInput]]:
    ranked = rank_skills(skills)
    chosen: list[tuple[PlanSkillInput, PlanProblemInput]] = []
    used_skills: set[str] = set()
    for skill in ranked:
        if len(chosen) >= slots:
            break
        picked = pick_problem_for_skill(skill, problems, used_ids, len(chosen))
        if picked is None:
            continue
        chosen.append((skill, picked))
        used_ids.add(picked.problem_id)
        used_skills.add(skill.slug)

    if len(chosen) < slots:
        for skill in ranked:
            if len(chosen) >= slots:
                break
            picked = pick_problem_for_skill(skill, problems, used_ids, len(chosen))
            if picked is None:
                continue
            chosen.append((skill, picked))
            used_ids.add(picked.problem_id)
    return chosen


def _lead_dimension(
    dsa: PlanDimensionInput | None,
    core_cs: PlanDimensionInput | None,
    target: PlanTargetInput,
    bias_dimension: ReadinessDimension | None,
) -> ReadinessDimension:
    if bias_dimension in {ReadinessDimension.DSA, ReadinessDimension.CORE_CS}:
        return bias_dimension
    dsa_focus = dimension_needs_focus(dsa)
    cs_focus = dimension_needs_focus(core_cs)
    if cs_focus and not dsa_focus:
        return ReadinessDimension.CORE_CS
    if dsa_focus and not cs_focus:
        return ReadinessDimension.DSA
    if target.core_cs_weight > target.dsa_weight:
        return ReadinessDimension.CORE_CS
    return ReadinessDimension.DSA


def interleave_items(
    dsa_pairs: list[tuple[PlanSkillInput, PlanProblemInput]],
    cs_pairs: list[tuple[PlanSkillInput, PlanProblemInput]],
    lead: ReadinessDimension,
) -> list[tuple[PlanSkillInput, PlanProblemInput]]:
    primary = cs_pairs if lead == ReadinessDimension.CORE_CS else dsa_pairs
    secondary = dsa_pairs if lead == ReadinessDimension.CORE_CS else cs_pairs
    merged: list[tuple[PlanSkillInput, PlanProblemInput]] = []
    i = 0
    j = 0
    while i < len(primary) or j < len(secondary):
        if i < len(primary):
            merged.append(primary[i])
            i += 1
        if j < len(secondary):
            merged.append(secondary[j])
            j += 1
    return merged


def make_assessment_id(user_id: str, problem_slugs: tuple[str, ...]) -> str:
    digest = sha256(f"{user_id}|{'|'.join(problem_slugs)}".encode()).hexdigest()
    return str(UUID(digest[:32]))


def build_assessment_plan(
    *,
    user_id: str,
    target: PlanTargetInput,
    skills: list[PlanSkillInput],
    problems: list[PlanProblemInput],
    dimensions: list[PlanDimensionInput],
    bias_dimension: ReadinessDimension | None = None,
) -> AssessmentPlan:
    by_key = {item.key: item for item in dimensions}
    dsa_dim = by_key.get(ReadinessDimension.DSA)
    cs_dim = by_key.get(ReadinessDimension.CORE_CS)
    dsa_slots, cs_slots = allocate_slots(dsa_dim, cs_dim, target, bias_dimension)

    dsa_skills = [skill for skill in skills if skill.dimension == ReadinessDimension.DSA]
    cs_skills = [skill for skill in skills if skill.dimension == ReadinessDimension.CORE_CS]
    used_ids: set[str] = set()
    dsa_pairs = _fill_dimension(dsa_skills, problems, dsa_slots, used_ids)
    cs_pairs = _fill_dimension(cs_skills, problems, cs_slots, used_ids)
    lead = _lead_dimension(dsa_dim, cs_dim, target, bias_dimension)
    ordered = interleave_items(dsa_pairs, cs_pairs, lead)

    items: list[AssessmentPlanItem] = []
    for position, (skill, problem) in enumerate(ordered, start=1):
        items.append(
            AssessmentPlanItem(
                position=position,
                activity_kind=problem.activity_kind,
                problem_id=problem.problem_id,
                problem_slug=problem.slug,
                problem_title=problem.title,
                dimension=skill.dimension,
                skill_slug=skill.slug,
                skill_name=skill.name,
                estimated_minutes=problem.estimated_minutes,
                difficulty=problem.difficulty,
            )
        )

    slugs = tuple(item.problem_slug for item in items)
    return AssessmentPlan(
        assessment_id=make_assessment_id(user_id, slugs),
        target_slug=target.slug,
        target_name=target.name,
        items=tuple(items),
        dsa_slots=dsa_slots,
        cs_slots=cs_slots,
    )
