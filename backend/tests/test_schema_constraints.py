from decimal import Decimal

import pytest
from app.core.enums import AttemptStatus, Difficulty, EvidencePolarity, MasteryStatus, MistakeType
from app.models import (
    Attempt,
    EvidenceItem,
    Problem,
    ProblemSkill,
    Skill,
    SkillDependency,
    Topic,
    User,
)
from app.seed.runner import (
    ALL_DEPENDENCIES,
    ALL_PROBLEMS,
    ALL_SKILLS,
    ALL_TOPICS,
    run_seed,
    validate_skill_graph_is_acyclic,
)
from sqlalchemy import select, text
from sqlalchemy.exc import DataError, IntegrityError


def test_seed_script_succeeds(db_session) -> None:
    counts = run_seed(db_session, commit=False)
    assert counts["topics"] == len(ALL_TOPICS)
    assert counts["skills"] == len(ALL_SKILLS)
    assert counts["problems"] == len(ALL_PROBLEMS)
    assert counts["dependencies"] == len(ALL_DEPENDENCIES)
    assert counts["hints"] == sum(len(p["hints"]) for p in ALL_PROBLEMS)


def test_seed_skill_graph_is_acyclic() -> None:
    validate_skill_graph_is_acyclic(ALL_DEPENDENCIES)


def test_seed_problem_skill_mappings(db_session) -> None:
    run_seed(db_session, commit=False)
    problems = db_session.scalars(select(Problem)).all()
    for problem in problems:
        links = db_session.scalars(
            select(ProblemSkill).where(ProblemSkill.problem_id == problem.id)
        ).all()
        assert len(links) >= 1
        primary_weights = [link.weight for link in links if link.weight == Decimal("1.0")]
        assert len(primary_weights) >= 1


def test_unique_email_constraint(db_session) -> None:
    db_session.add(
        User(
            email="learner@example.com",
            password_hash="hash",
            display_name="Learner",
        )
    )
    db_session.flush()
    db_session.add(
        User(
            email="learner@example.com",
            password_hash="hash2",
            display_name="Duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_unique_topic_and_problem_slug_constraints(db_session) -> None:
    run_seed(db_session, commit=False)
    topic = db_session.scalar(select(Topic).limit(1))
    problem = db_session.scalar(select(Problem).limit(1))
    topic_slug = topic.slug
    topic_id = topic.id
    problem_slug = problem.slug

    db_session.add(Topic(slug=topic_slug, name="Duplicate Topic", sort_order=99))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        Problem(
            slug=problem_slug,
            title="Duplicate",
            prompt_md="x",
            difficulty=Difficulty.EASY,
            estimated_minutes=10,
            topic_id=topic_id,
            is_published=True,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_problem_skill_rejected(db_session) -> None:
    run_seed(db_session, commit=False)
    problem = db_session.scalar(select(Problem).limit(1))
    link = db_session.scalar(
        select(ProblemSkill).where(ProblemSkill.problem_id == problem.id).limit(1)
    )
    db_session.add(
        ProblemSkill(
            problem_id=problem.id,
            skill_id=link.skill_id,
            weight=Decimal("0.5"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_skill_dependency_rejected(db_session) -> None:
    run_seed(db_session, commit=False)
    dependency = db_session.scalar(select(SkillDependency).limit(1))
    db_session.add(
        SkillDependency(
            prerequisite_skill_id=dependency.prerequisite_skill_id,
            skill_id=dependency.skill_id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_self_skill_dependency_rejected(db_session) -> None:
    run_seed(db_session, commit=False)
    skill = db_session.scalar(select(Skill).limit(1))
    db_session.add(
        SkillDependency(
            prerequisite_skill_id=skill.id,
            skill_id=skill.id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_only_one_in_progress_attempt_per_user_problem(db_session) -> None:
    run_seed(db_session, commit=False)
    user = User(email="attempt@example.com", password_hash="hash", display_name="Attempt User")
    problem = db_session.scalar(select(Problem).limit(1))
    db_session.add(user)
    db_session.flush()

    db_session.add(
        Attempt(
            user_id=user.id,
            problem_id=problem.id,
            status=AttemptStatus.IN_PROGRESS,
            client_attempt_id="client-1",
        )
    )
    db_session.flush()

    db_session.add(
        Attempt(
            user_id=user.id,
            problem_id=problem.id,
            status=AttemptStatus.IN_PROGRESS,
            client_attempt_id="client-2",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_foreign_key_rejects_invalid_problem_reference(db_session) -> None:
    run_seed(db_session, commit=False)
    user = User(email="fk@example.com", password_hash="hash", display_name="FK User")
    db_session.add(user)
    db_session.flush()

    db_session.add(
        Attempt(
            user_id=user.id,
            problem_id="00000000-0000-0000-0000-000000000001",
            status=AttemptStatus.IN_PROGRESS,
            client_attempt_id="fk-client",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_postgresql_enum_labels_are_lowercase(db_session, test_engine) -> None:
    run_seed(db_session, commit=False)

    with test_engine.connect() as connection:
        difficulty_labels = (
            connection.execute(
                text(
                    """
                SELECT e.enumlabel
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'difficulty'
                ORDER BY e.enumsortorder
                """
                )
            )
            .scalars()
            .all()
        )
        attempt_status_labels = (
            connection.execute(
                text(
                    """
                SELECT e.enumlabel
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'attempt_status'
                ORDER BY e.enumsortorder
                """
                )
            )
            .scalars()
            .all()
        )

    assert difficulty_labels == ["easy", "medium", "hard"]
    assert attempt_status_labels == ["in_progress", "submitted", "abandoned"]

    stored_difficulty = db_session.execute(
        text("SELECT difficulty::text FROM problems ORDER BY slug LIMIT 1")
    ).scalar_one()
    assert stored_difficulty == "easy"


def test_enum_values_are_enforced(db_session) -> None:
    run_seed(db_session, commit=False)
    user = User(email="enum@example.com", password_hash="hash", display_name="Enum User")
    problem = db_session.scalar(select(Problem).limit(1))
    db_session.add(user)
    db_session.flush()

    attempt = Attempt(
        user_id=user.id,
        problem_id=problem.id,
        status=AttemptStatus.SUBMITTED,
        client_attempt_id="enum-client",
        is_correct=False,
        mistake_type=MistakeType.LOGIC_ERROR,
    )
    db_session.add(attempt)
    db_session.flush()

    skill = db_session.scalar(select(Skill).limit(1))
    db_session.add(
        EvidenceItem(
            user_id=user.id,
            skill_id=skill.id,
            attempt_id=attempt.id,
            evidence_type="failed_attempt",
            polarity=EvidencePolarity.NEGATIVE,
            strength=Decimal("0.5"),
            summary_text="Failed attempt",
            details={"problem_slug": problem.slug},
        )
    )
    db_session.flush()

    from app.models import SkillMastery

    db_session.add(
        SkillMastery(
            user_id=user.id,
            skill_id=skill.id,
            score=Decimal("0.25"),
            confidence=Decimal("0.3"),
            evidence_count=1,
            status=MasteryStatus.INSUFFICIENT,
        )
    )
    db_session.flush()

    assert attempt.mistake_type == MistakeType.LOGIC_ERROR
    assert attempt.status == AttemptStatus.SUBMITTED

    with pytest.raises((IntegrityError, DataError)):
        db_session.execute(
            text("UPDATE attempts SET status = 'invalid' WHERE id = :id"),
            {"id": attempt.id},
        )


def test_target_profile_slug_unique(db_session) -> None:
    from app.models.readiness import TargetProfile

    db_session.add(
        TargetProfile(slug="dup-profile", name="One", description="d", is_system=True, sort_order=1)
    )
    db_session.flush()
    db_session.add(
        TargetProfile(slug="dup-profile", name="Two", description="d", is_system=True, sort_order=2)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_one_learner_target_per_user(db_session) -> None:
    from app.models.readiness import LearnerTarget, TargetProfile

    run_seed(db_session, commit=False)
    profile = db_session.scalar(select(TargetProfile).limit(1))
    user = User(
        email="one-target@example.com",
        password_hash="hash",
        display_name="One Target",
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(LearnerTarget(user_id=user.id, profile_id=profile.id))
    db_session.flush()
    db_session.add(LearnerTarget(user_id=user.id, profile_id=profile.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dimension_skill_uniqueness(db_session) -> None:
    from app.models.readiness import DimensionSkill

    run_seed(db_session, commit=False)
    skill = db_session.scalar(select(Skill).limit(1))
    db_session.add(DimensionSkill(dimension="dsa", skill_id=skill.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_requirement_belongs_to_target(db_session) -> None:
    from uuid import uuid4

    from app.models.readiness import TargetRequirement

    run_seed(db_session, commit=False)
    db_session.add(
        TargetRequirement(
            profile_id=uuid4(),
            dimension="dsa",
            min_score=Decimal("0.7"),
            min_confidence=Decimal("0.5"),
            weight=Decimal("0.4"),
            is_critical=True,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
