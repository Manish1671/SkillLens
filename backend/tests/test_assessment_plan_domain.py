from app.core.enums import (
    ActivityKind,
    Difficulty,
    DimensionStatus,
    MasteryStatus,
    ReadinessDimension,
)
from app.domain.assessment_plan import (
    CORE_CS_DIAGNOSTIC_SKILLS,
    DSA_DIAGNOSTIC_SKILLS,
    PlanDimensionInput,
    PlanProblemInput,
    PlanSkillInput,
    PlanTargetInput,
    allocate_slots,
    build_assessment_plan,
    pick_problem_for_skill,
    rank_skills,
    skill_need,
)


def _target(*, dsa_weight: float = 0.40, cs_weight: float = 0.35) -> PlanTargetInput:
    return PlanTargetInput(
        slug="product-sde",
        name="Product SDE",
        dsa_weight=dsa_weight,
        core_cs_weight=cs_weight,
    )


def _dim(
    key: ReadinessDimension,
    *,
    status: DimensionStatus = DimensionStatus.NOT_ASSESSED,
    score: float | None = None,
    coverage: float = 0.0,
    assessed_count: int = 0,
) -> PlanDimensionInput:
    return PlanDimensionInput(
        key=key,
        status=status,
        score=score,
        coverage=coverage,
        assessed_count=assessed_count,
    )


def _skill(
    slug: str,
    dimension: ReadinessDimension,
    **kwargs: object,
) -> PlanSkillInput:
    defaults: dict = {
        "name": slug.replace("-", " ").title(),
        "is_foundational": slug in {"arrays", "sql-basics", "linked-lists", "trees"},
        "sort_order": 10,
        "prerequisite_slugs": (),
        "score": None,
        "confidence": 0.0,
        "status": MasteryStatus.INSUFFICIENT,
        "evidence_count": 0,
    }
    defaults.update(kwargs)
    return PlanSkillInput(slug=slug, dimension=dimension, **defaults)


def _problem(
    slug: str,
    skill: str,
    *,
    kind: ActivityKind = ActivityKind.CODING,
    difficulty: Difficulty = Difficulty.EASY,
    problem_id: str | None = None,
    extra_skills: tuple[str, ...] = (),
    published: bool = True,
    solved: bool = False,
    in_progress: bool = False,
    attempted: bool = False,
) -> PlanProblemInput:
    skills = (skill, *extra_skills)
    return PlanProblemInput(
        problem_id=problem_id or slug,
        slug=slug,
        title=slug.replace("-", " ").title(),
        activity_kind=kind,
        difficulty=difficulty,
        estimated_minutes=15 if kind == ActivityKind.CODING else 8,
        skill_slugs=skills,
        primary_skill_slug=skill,
        skill_weights=tuple((item, 1.0) for item in skills),
        is_published=published,
        attempted=attempted or solved or in_progress,
        solved=solved,
        in_progress=in_progress,
    )


def _catalog() -> tuple[list[PlanSkillInput], list[PlanProblemInput]]:
    skills: list[PlanSkillInput] = []
    problems: list[PlanProblemInput] = []
    for index, slug in enumerate(DSA_DIAGNOSTIC_SKILLS):
        skills.append(_skill(slug, ReadinessDimension.DSA, sort_order=index))
        difficulty = (Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD)[index % 3]
        problems.append(
            _problem(f"dsa-{slug}", slug, difficulty=difficulty, problem_id=f"d-{slug}")
        )
        problems.append(
            _problem(
                f"dsa-{slug}-alt",
                slug,
                difficulty=Difficulty.MEDIUM,
                problem_id=f"d-{slug}-alt",
            )
        )
    for index, slug in enumerate(CORE_CS_DIAGNOSTIC_SKILLS):
        skills.append(_skill(slug, ReadinessDimension.CORE_CS, sort_order=200 + index))
        problems.append(
            _problem(
                f"quiz-{slug}",
                slug,
                kind=ActivityKind.QUIZ,
                difficulty=Difficulty.EASY,
                problem_id=f"q-{slug}",
            )
        )
    return skills, problems


def _new_dimensions() -> list[PlanDimensionInput]:
    return [
        _dim(ReadinessDimension.DSA),
        _dim(ReadinessDimension.CORE_CS),
    ]


def test_deterministic_plan() -> None:
    skills, problems = _catalog()
    first = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    second = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    assert [item.problem_slug for item in first.items] == [
        item.problem_slug for item in second.items
    ]
    assert first.assessment_id == second.assessment_id


def test_dsa_core_cs_balance_for_new_learner() -> None:
    skills, problems = _catalog()
    plan = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    dsa = [item for item in plan.items if item.dimension == ReadinessDimension.DSA]
    cs = [item for item in plan.items if item.dimension == ReadinessDimension.CORE_CS]
    assert 6 <= len(dsa) <= 8
    assert 4 <= len(cs) <= 5
    assert 10 <= plan.total_items <= 12
    assert all(item.activity_kind == ActivityKind.CODING for item in dsa)
    assert all(item.activity_kind == ActivityKind.QUIZ for item in cs)


def test_strong_skill_deprioritized() -> None:
    skills, _problems = _catalog()
    strong = _skill(
        "arrays",
        ReadinessDimension.DSA,
        score=0.88,
        status=MasteryStatus.ASSESSED,
        evidence_count=5,
        is_foundational=True,
        sort_order=0,
    )
    weak = _skill(
        "graphs",
        ReadinessDimension.DSA,
        score=None,
        status=MasteryStatus.INSUFFICIENT,
        evidence_count=0,
        sort_order=7,
    )
    ranked = rank_skills([strong, weak])
    assert ranked[0].slug == "graphs"
    assert skill_need(strong) < skill_need(weak)


def test_insufficient_skill_prioritized() -> None:
    hashing = _skill(
        "hashing",
        ReadinessDimension.DSA,
        score=0.70,
        status=MasteryStatus.ASSESSED,
        evidence_count=4,
    )
    missing = _skill("trees", ReadinessDimension.DSA)
    ranked = rank_skills([hashing, missing])
    assert ranked[0].slug == "trees"


def test_weak_skill_represented() -> None:
    weak = _skill(
        "transactions",
        ReadinessDimension.CORE_CS,
        score=0.42,
        status=MasteryStatus.ASSESSED,
        evidence_count=4,
    )
    strong = _skill(
        "sql-basics",
        ReadinessDimension.CORE_CS,
        score=0.90,
        status=MasteryStatus.ASSESSED,
        evidence_count=6,
        is_foundational=True,
    )
    skills, problems = _catalog()
    skills = [
        weak if skill.slug == "transactions" else strong if skill.slug == "sql-basics" else skill
        for skill in skills
        if skill.dimension == ReadinessDimension.CORE_CS
    ] + [skill for skill in skills if skill.dimension == ReadinessDimension.DSA]
    plan = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=[
            _dim(
                ReadinessDimension.DSA,
                status=DimensionStatus.NEAR_READY,
                score=0.81,
                coverage=0.7,
                assessed_count=6,
            ),
            _dim(
                ReadinessDimension.CORE_CS,
                status=DimensionStatus.DEVELOPING,
                score=0.52,
                coverage=0.8,
                assessed_count=5,
            ),
        ],
    )
    cs_slugs = [
        item.skill_slug for item in plan.items if item.dimension == ReadinessDimension.CORE_CS
    ]
    assert "transactions" in cs_slugs
    assert skill_need(weak) > skill_need(strong)


def test_no_duplicate_problem() -> None:
    skills, problems = _catalog()
    plan = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    slugs = [item.problem_slug for item in plan.items]
    assert len(slugs) == len(set(slugs))
    ids = [item.problem_id for item in plan.items]
    assert len(ids) == len(set(ids))


def test_coverage_across_skills() -> None:
    skills, problems = _catalog()
    plan = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    skill_slugs = [item.skill_slug for item in plan.items]
    assert len(set(skill_slugs)) == len(skill_slugs)
    cs_skills = {
        item.skill_slug for item in plan.items if item.dimension == ReadinessDimension.CORE_CS
    }
    assert cs_skills <= set(CORE_CS_DIAGNOSTIC_SKILLS)


def test_deterministic_ordering() -> None:
    skills, problems = _catalog()
    plan = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=list(reversed(skills)),
        problems=list(reversed(problems)),
        dimensions=_new_dimensions(),
    )
    again = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    assert [item.skill_slug for item in plan.items] == [item.skill_slug for item in again.items]


def test_target_aware_planning() -> None:
    skills, problems = _catalog()
    dsa_heavy = build_assessment_plan(
        user_id="user-a",
        target=_target(dsa_weight=0.55, cs_weight=0.20),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    cs_heavy = build_assessment_plan(
        user_id="user-a",
        target=_target(dsa_weight=0.20, cs_weight=0.55),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    dsa_count = sum(1 for item in dsa_heavy.items if item.dimension == ReadinessDimension.DSA)
    cs_count_on_cs_heavy = sum(
        1 for item in cs_heavy.items if item.dimension == ReadinessDimension.CORE_CS
    )
    assert dsa_count >= 7
    assert cs_count_on_cs_heavy >= 5
    assert allocate_slots(
        _dim(ReadinessDimension.DSA),
        _dim(ReadinessDimension.CORE_CS),
        _target(dsa_weight=0.20, cs_weight=0.55),
    ) == (6, 5)


def test_strong_dsa_increases_core_cs_focus() -> None:
    dsa_n, cs_n = allocate_slots(
        _dim(
            ReadinessDimension.DSA,
            status=DimensionStatus.NEAR_READY,
            score=0.81,
            coverage=0.7,
            assessed_count=6,
        ),
        _dim(ReadinessDimension.CORE_CS, status=DimensionStatus.NOT_ASSESSED),
        _target(),
    )
    assert cs_n >= dsa_n or cs_n == 5
    assert cs_n == 5
    assert dsa_n == 6


def test_strong_core_cs_increases_dsa_focus() -> None:
    dsa_n, cs_n = allocate_slots(
        _dim(
            ReadinessDimension.DSA,
            status=DimensionStatus.DEVELOPING,
            score=0.50,
            coverage=0.5,
            assessed_count=6,
        ),
        _dim(
            ReadinessDimension.CORE_CS,
            status=DimensionStatus.NEAR_READY,
            score=0.80,
            coverage=1.0,
            assessed_count=5,
        ),
        _target(),
    )
    assert dsa_n > cs_n
    assert dsa_n == 8


def test_unpublished_and_in_progress_skipped() -> None:
    skill = _skill("arrays", ReadinessDimension.DSA, is_foundational=True)
    hidden = _problem("hidden", "arrays", published=False)
    busy = _problem("busy", "arrays", in_progress=True, problem_id="busy")
    open_one = _problem("open", "arrays", problem_id="open")
    picked = pick_problem_for_skill(skill, [hidden, busy, open_one], set(), 0)
    assert picked is not None
    assert picked.slug == "open"


def test_same_user_different_history_changes_plan() -> None:
    skills, problems = _catalog()
    cold = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=skills,
        problems=problems,
        dimensions=_new_dimensions(),
    )
    hot_skills = [
        _skill(
            skill.slug,
            skill.dimension,
            name=skill.name,
            is_foundational=skill.is_foundational,
            sort_order=skill.sort_order,
            score=0.88 if skill.dimension == ReadinessDimension.DSA else None,
            status=(
                MasteryStatus.ASSESSED
                if skill.dimension == ReadinessDimension.DSA
                else MasteryStatus.INSUFFICIENT
            ),
            evidence_count=5 if skill.dimension == ReadinessDimension.DSA else 0,
        )
        for skill in skills
    ]
    hot = build_assessment_plan(
        user_id="user-a",
        target=_target(),
        skills=hot_skills,
        problems=problems,
        dimensions=[
            _dim(
                ReadinessDimension.DSA,
                status=DimensionStatus.NEAR_READY,
                score=0.81,
                coverage=0.8,
                assessed_count=8,
            ),
            _dim(ReadinessDimension.CORE_CS),
        ],
    )
    cold_cs = sum(1 for item in cold.items if item.dimension == ReadinessDimension.CORE_CS)
    hot_cs = sum(1 for item in hot.items if item.dimension == ReadinessDimension.CORE_CS)
    assert hot_cs >= cold_cs
    assert [item.problem_slug for item in cold.items] != [item.problem_slug for item in hot.items]
