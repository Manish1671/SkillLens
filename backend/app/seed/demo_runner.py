from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    AttemptEventType,
    AttemptStatus,
    DimensionStatus,
    MasteryStatus,
    PlacementActionKind,
    ReadinessDimension,
)
from app.core.security import hash_password, normalize_email
from app.core.services import (
    assessment_service,
    attempt_service,
    placement_action_service,
    readiness_service,
    recommendation_service,
)
from app.domain.mastery import compute_mastery
from app.domain.recommendation import STATE_COLD_START, STATE_PREREQUISITE_BLOCKED
from app.models.assessment import (
    EvidenceItem,
    Recommendation,
    SkillAssessmentSnapshot,
    SkillMastery,
)
from app.models.attempt import Attempt, AttemptEvent
from app.models.placement_action import PlacementAction
from app.models.problem import Problem
from app.models.readiness import LearnerTarget
from app.models.user import User
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.schemas.attempt import RecordAttemptEventRequest, StartAttemptRequest, SubmitAttemptRequest
from app.seed.core_cs_data import CORE_CS_SKILL_SLUGS
from app.seed.demo_script import (
    DEMO_ATTEMPTS,
    DEMO_DISPLAY_NAME,
    DEMO_EMAIL,
    DEMO_PASSWORD_ENV,
    DSA_IN_SCOPE_COUNT,
    MIN_DSA_ASSESSED_FOR_COVERAGE,
    DemoAttemptSpec,
)
from app.seed.runner import run_seed


class DemoSeedError(RuntimeError):
    pass


def require_demo_password() -> str:
    password = os.environ.get(DEMO_PASSWORD_ENV, "").strip()
    if not password:
        raise DemoSeedError(
            f"{DEMO_PASSWORD_ENV} is not set. "
            "Set it in the environment before seeding the demo account."
        )
    if len(password) < 8:
        raise DemoSeedError(f"{DEMO_PASSWORD_ENV} must be at least 8 characters.")
    return password


def _ensure_catalog(session: Session) -> None:
    count = session.scalar(select(func.count()).select_from(Problem)) or 0
    if count == 0:
        run_seed(session, commit=False)


def _upsert_demo_user(session: Session, password: str) -> User:
    users = UserRepository()
    email = normalize_email(DEMO_EMAIL)
    user = users.find_by_email(session, email)
    password_hash = hash_password(password)
    if user is None:
        user = users.create(
            session,
            email=email,
            password_hash=password_hash,
            display_name=DEMO_DISPLAY_NAME,
        )
    else:
        user.password_hash = password_hash
        user.display_name = DEMO_DISPLAY_NAME
    session.flush()
    return user


def clear_demo_learner_state(session: Session, user_id: UUID) -> None:
    attempt_ids = list(session.scalars(select(Attempt.id).where(Attempt.user_id == user_id)))
    session.execute(delete(LearnerTarget).where(LearnerTarget.user_id == user_id))
    session.execute(delete(PlacementAction).where(PlacementAction.user_id == user_id))
    session.execute(delete(Recommendation).where(Recommendation.user_id == user_id))
    session.execute(
        delete(SkillAssessmentSnapshot).where(SkillAssessmentSnapshot.user_id == user_id)
    )
    session.execute(delete(EvidenceItem).where(EvidenceItem.user_id == user_id))
    if attempt_ids:
        session.execute(delete(AttemptEvent).where(AttemptEvent.attempt_id.in_(attempt_ids)))
        session.execute(delete(Attempt).where(Attempt.user_id == user_id))
    session.execute(delete(SkillMastery).where(SkillMastery.user_id == user_id))
    session.flush()


def _occurred_at(spec: DemoAttemptSpec, *, now: datetime) -> tuple[datetime, datetime]:
    # Offset from *now* so recency is deterministic regardless of time of day.
    submitted = now - timedelta(
        days=spec.days_ago,
        hours=spec.hour % 8,
        minutes=spec.minute,
    )
    started = submitted - timedelta(seconds=spec.time_spent_seconds + 40)
    return started, submitted


def _play_attempt(session: Session, user: User, spec: DemoAttemptSpec) -> Attempt:
    problems = ProblemRepository()
    problem = problems.find_published_by_slug(session, spec.problem_slug)
    if problem is None:
        raise DemoSeedError(
            f"Catalog problem '{spec.problem_slug}' is missing. Run `python -m app.seed` first."
        )

    started = attempt_service.start_attempt(
        session,
        user,
        StartAttemptRequest(problem_id=problem.id, client_attempt_id=spec.client_attempt_id),
    )
    attempt_id = UUID(started.id)

    hints = sorted(problem.hints, key=lambda hint: hint.ordinal)
    for hint in hints[: spec.hint_count]:
        attempt_service.record_event(
            session,
            user,
            attempt_id,
            RecordAttemptEventRequest(
                event_type=AttemptEventType.HINT_REVEALED,
                payload={"hint_id": str(hint.id)},
            ),
        )

    attempt_service.submit_attempt(
        session,
        user,
        attempt_id,
        SubmitAttemptRequest(
            is_correct=spec.is_correct,
            time_spent_seconds=spec.time_spent_seconds,
            mistake_type=spec.mistake_type,
        ),
    )
    attempt = session.get(Attempt, attempt_id)
    if attempt is None:
        raise DemoSeedError(f"Attempt {spec.client_attempt_id} was not persisted.")
    return attempt


def _stamp_history(
    session: Session, attempt: Attempt, started_at: datetime, submitted_at: datetime
) -> None:
    attempt.started_at = started_at
    attempt.submitted_at = submitted_at
    attempt.created_at = started_at
    attempt.updated_at = submitted_at

    events = list(
        session.scalars(select(AttemptEvent).where(AttemptEvent.attempt_id == attempt.id)).all()
    )
    events.sort(key=lambda event: event.occurred_at)
    if events:
        span = max(1, (submitted_at - started_at).total_seconds())
        for index, event in enumerate(events):
            when = started_at + timedelta(seconds=span * index / max(1, len(events) - 1))
            if event.event_type == AttemptEventType.STARTED:
                when = started_at
            if event.event_type == AttemptEventType.SUBMITTED:
                when = submitted_at
            event.occurred_at = when
            event.created_at = when

    for item in session.scalars(select(EvidenceItem).where(EvidenceItem.attempt_id == attempt.id)):
        item.created_at = submitted_at
    for snap in session.scalars(
        select(SkillAssessmentSnapshot).where(SkillAssessmentSnapshot.attempt_id == attempt.id)
    ):
        snap.computed_at = submitted_at
        snap.created_at = submitted_at
    for rec in session.scalars(
        select(Recommendation).where(Recommendation.source_attempt_id == attempt.id)
    ):
        rec.generated_at = submitted_at
        rec.created_at = submitted_at
    session.flush()


def _refresh_mastery_from_evidence(session: Session, user_id: UUID, reference: datetime) -> None:
    """Recompute current SkillMastery from stored evidence (domain compute_mastery)."""
    masteries = list(session.scalars(select(SkillMastery).where(SkillMastery.user_id == user_id)))
    skills_by_id = {row.skill_id: row for row in masteries}
    for skill_id in skills_by_id:
        rows = assessment_service._evidence.list_for_user_skill(session, user_id, skill_id)
        evidence_inputs = assessment_service._to_evidence_inputs(rows)
        prereq_pairs = assessment_service._mastery.get_prerequisite_scores(
            session, user_id, skill_id
        )
        prereq_scores = [score for _, score in prereq_pairs]
        result = compute_mastery(evidence_inputs, reference, prereq_scores)
        last_attempt = max((row.created_at for row in rows), default=reference)
        assessment_service._mastery.upsert(
            session,
            user_id=user_id,
            skill_id=skill_id,
            score=Decimal(str(result.score)),
            confidence=Decimal(str(result.confidence)),
            evidence_count=len(rows),
            last_attempt_at=last_attempt,
            status=result.status,
        )
    session.flush()


def seed_demo_account(
    session: Session, *, password: str | None = None, commit: bool = True
) -> dict:
    secret = password if password is not None else require_demo_password()
    _ensure_catalog(session)
    user = _upsert_demo_user(session, secret)
    clear_demo_learner_state(session, user.id)

    now = datetime.now(UTC)
    for spec in DEMO_ATTEMPTS:
        attempt = _play_attempt(session, user, spec)
        started_at, submitted_at = _occurred_at(spec, now=now)
        session.refresh(attempt)
        _stamp_history(session, attempt, started_at, submitted_at)

    _refresh_mastery_from_evidence(session, user.id, now)
    recommendation_service.get_next(session, user.id, refresh=True)
    readiness_service.set_learner_target(session, user, "product-sde")
    placement_action_service.get_actions(session, user.id, refresh=True, commit=False, limit=5)

    if commit:
        session.commit()
        session.refresh(user)
    else:
        session.flush()

    return summarize_demo(session, user.id)


def summarize_demo(session: Session, user_id: UUID) -> dict:
    user = session.get(User, user_id)
    assert user is not None
    attempt_count = (
        session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id))
        or 0
    )
    in_progress = (
        session.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(Attempt.user_id == user_id, Attempt.status == AttemptStatus.IN_PROGRESS)
        )
        or 0
    )
    evidence_count = (
        session.scalar(
            select(func.count()).select_from(EvidenceItem).where(EvidenceItem.user_id == user_id)
        )
        or 0
    )
    snapshot_count = (
        session.scalar(
            select(func.count())
            .select_from(SkillAssessmentSnapshot)
            .where(SkillAssessmentSnapshot.user_id == user_id)
        )
        or 0
    )
    rec_count = (
        session.scalar(
            select(func.count())
            .select_from(Recommendation)
            .where(Recommendation.user_id == user_id)
        )
        or 0
    )
    action_count = (
        session.scalar(
            select(func.count())
            .select_from(PlacementAction)
            .where(PlacementAction.user_id == user_id)
        )
        or 0
    )
    foreign_evidence = session.scalar(
        select(func.count()).select_from(EvidenceItem).where(EvidenceItem.user_id != user_id)
    )

    mastery = assessment_service.get_user_mastery(session, user_id)
    assessed = [item for item in mastery.items if item.status == MasteryStatus.ASSESSED]
    dsa_assessed = [item for item in assessed if item.skill_slug not in CORE_CS_SKILL_SLUGS]
    core_cs_items = [item for item in mastery.items if item.skill_slug in CORE_CS_SKILL_SLUGS]
    insufficient = [item for item in mastery.items if item.status != MasteryStatus.ASSESSED]
    strengths = sorted(
        dsa_assessed,
        key=lambda item: float(item.score or 0),
        reverse=True,
    )
    weakest = sorted(dsa_assessed, key=lambda item: float(item.score or 1))
    next_rec = recommendation_service.get_next(session, user_id, refresh=False)
    focus = next_rec.target_skill
    readiness = readiness_service.get_readiness(session, user_id)
    next_action = placement_action_service.get_next(session, user_id, refresh=False, commit=False)
    action_rows = list(
        session.scalars(select(PlacementAction).where(PlacementAction.user_id == user_id))
    )
    warnings = _collect_warnings(
        session,
        user_id,
        assessed=assessed,
        next_rec=next_rec,
        attempt_count=int(attempt_count),
        in_progress=int(in_progress),
        action_rows=action_rows,
        core_cs_items=core_cs_items,
    )
    dim_map = {item.key: item for item in readiness.dimensions}
    dsa_dim = dim_map.get(ReadinessDimension.DSA)
    core_dim = dim_map.get(ReadinessDimension.CORE_CS)
    projects_dim = dim_map.get(ReadinessDimension.PROJECTS)
    interview_dim = dim_map.get(ReadinessDimension.INTERVIEW)
    profile_dim = dim_map.get(ReadinessDimension.PROFILE)
    strongest = strengths[0] if strengths else None
    weakest_skill = weakest[0] if weakest else None

    return {
        "email": user.email,
        "display_name": user.display_name,
        "target_name": readiness.target.name if readiness.target else None,
        "attempts": int(attempt_count),
        "in_progress_attempts": int(in_progress),
        "evidence": int(evidence_count),
        "snapshots": int(snapshot_count),
        "recommendations": int(rec_count),
        "placement_actions": int(action_count),
        "assessed_skills": len(assessed),
        "dsa_assessed_count": len(dsa_assessed),
        "dsa_in_scope": DSA_IN_SCOPE_COUNT,
        "insufficient_skills": len(insufficient),
        "mastery": mastery.items,
        "top_strengths": [
            f"{item.skill_name} ({(float(item.score) * 100):.0f}%, "
            f"{_confidence_band(item.confidence)})"
            for item in strengths[:4]
            if item.score
        ],
        "strongest_skill": strongest.skill_name if strongest else None,
        "strongest_slug": strongest.skill_slug if strongest else None,
        "strongest_score": strongest.score if strongest else None,
        "weakest_skill": weakest_skill.skill_name if weakest_skill else None,
        "weakest_slug": weakest_skill.skill_slug if weakest_skill else None,
        "weakest_score": weakest_skill.score if weakest_skill else None,
        "current_focus": focus.skill_name if focus else None,
        "focus_slug": focus.skill_slug if focus else None,
        "focus_mastery": focus.score if focus else None,
        "focus_confidence": focus.confidence if focus else None,
        "focus_status": focus.status.value if focus else None,
        "next_recommendation": (
            next_rec.recommendation.problem.title if next_rec.recommendation else None
        ),
        "next_reason_codes": (
            next_rec.recommendation.explanation.reason_codes if next_rec.recommendation else []
        ),
        "recommendation_state": next_rec.state,
        "recommendation_message": next_rec.message,
        "dsa_status": dsa_dim.status.value if dsa_dim else None,
        "dsa_score": dsa_dim.score if dsa_dim else None,
        "dsa_coverage": dsa_dim.coverage if dsa_dim else None,
        "dsa_requirement": (
            dsa_dim.requirement_status.value if dsa_dim and dsa_dim.requirement_status else None
        ),
        "core_cs_status": core_dim.status.value if core_dim else None,
        "core_cs_score": core_dim.score if core_dim else None,
        "projects_status": projects_dim.status.value if projects_dim else None,
        "interview_status": interview_dim.status.value if interview_dim else None,
        "profile_status": profile_dim.status.value if profile_dim else None,
        "placement_state": readiness.state.value,
        "next_action_kind": next_action.action.action_kind.value if next_action.action else None,
        "next_action_dimension": (
            next_action.action.target_dimension.value if next_action.action else None
        ),
        "next_action_title": next_action.action.title if next_action.action else None,
        "next_action_why": list(next_action.action.why) if next_action.action else [],
        "next_action_reason_codes": (
            list(next_action.action.reason_codes) if next_action.action else []
        ),
        "foreign_evidence_rows": int(foreign_evidence or 0),
        "expected_attempts": len(DEMO_ATTEMPTS),
        "warnings": warnings,
    }


def _confidence_band(confidence: str | None) -> str:
    value = float(confidence or 0)
    if value >= 0.7:
        return "high confidence"
    if value >= 0.4:
        return "medium confidence"
    return "low confidence"


def _collect_warnings(
    session: Session,
    user_id: UUID,
    *,
    assessed: list,
    next_rec,
    attempt_count: int,
    in_progress: int,
    action_rows: list[PlacementAction],
    core_cs_items: list,
) -> list[str]:
    warnings: list[str] = []
    for item in assessed:
        if item.score is None:
            warnings.append(f"assessed skill {item.skill_slug} has a null score")
            continue
        score = float(item.score)
        confidence = float(item.confidence)
        if score < 0.05 and confidence >= 0.7:
            warnings.append(
                f"{item.skill_name} has ~{score:.0%} mastery with unexpectedly high confidence"
            )
        if item.evidence_count < 1:
            warnings.append(f"assessed skill {item.skill_slug} has no evidence")
        if item.last_attempt_at is None:
            warnings.append(f"assessed skill {item.skill_slug} is missing last_attempt_at")

    if attempt_count > 0 and next_rec.state == STATE_COLD_START:
        warnings.append("cold_start recommendation state despite submitted attempts")
    if next_rec.state == STATE_PREREQUISITE_BLOCKED:
        warnings.append("recommendation blocked by prerequisite unexpectedly")
    if in_progress:
        warnings.append("in-progress attempts remain after seed")

    client_ids = list(
        session.scalars(select(Attempt.client_attempt_id).where(Attempt.user_id == user_id))
    )
    if len(client_ids) != len(set(client_ids)):
        warnings.append("duplicate attempt client_attempt_id values")

    evidence_keys = list(
        session.execute(
            select(
                EvidenceItem.attempt_id,
                EvidenceItem.skill_id,
                EvidenceItem.evidence_type,
            ).where(EvidenceItem.user_id == user_id)
        ).all()
    )
    if len(evidence_keys) != len(set(evidence_keys)):
        warnings.append("duplicate evidence rows for the same attempt/skill/type")

    action_keys = [
        (row.action_kind, row.target_dimension, row.target_skill_id, row.problem_id, row.rank)
        for row in action_rows
    ]
    if len(action_keys) != len(set(action_keys)):
        warnings.append("duplicate placement actions in the generated batch")
    if any(
        item.skill_slug in CORE_CS_SKILL_SLUGS and item.evidence_count > 0 for item in core_cs_items
    ):
        warnings.append("Core CS evidence was created on the initial demo seed")

    return warnings


def format_summary(summary: dict) -> str:
    strengths = "\n".join(f"  - {row}" for row in summary["top_strengths"]) or "  none yet"
    why = "\n".join(f"  {line}" for line in summary["next_action_why"]) or "  n/a"
    dsa_score = summary["dsa_score"]
    if dsa_score is not None:
        dsa_score_label = f"{(dsa_score * 100):.0f}%"
    else:
        dsa_score_label = "not enough evidence"
    strongest_score = summary["strongest_score"]
    weakest_score = summary["weakest_score"]
    lines = [
        "DEMO ACCOUNT READY",
        "",
        "Target:",
        f"  {summary['target_name'] or 'none'}",
        "",
        "Attempts:",
        f"  {summary['attempts']}",
        "",
        "Evidence:",
        f"  {summary['evidence']}",
        "",
        "DSA assessed:",
        f"  {summary['dsa_assessed_count']} / {summary['dsa_in_scope']}",
        "",
        "DSA strongest:",
        f"  {summary['strongest_skill'] or 'n/a'}"
        + (f" ({(float(strongest_score) * 100):.0f}%)" if strongest_score is not None else ""),
        "",
        "DSA weakest:",
        f"  {summary['weakest_skill'] or 'n/a'}"
        + (f" ({(float(weakest_score) * 100):.0f}%)" if weakest_score is not None else ""),
        "",
        "DSA readiness:",
        f"  {summary['dsa_status']} / {dsa_score_label} / {summary['dsa_requirement'] or 'n/a'}",
        "",
        "Core CS:",
        f"  {summary['core_cs_status']}",
        "",
        "Projects:",
        f"  {summary['projects_status']}",
        "",
        "Interview:",
        f"  {summary['interview_status']}",
        "",
        "Profile:",
        f"  {summary['profile_status']}",
        "",
        "Placement state:",
        f"  {summary['placement_state']}",
        "",
        "STRONGEST SKILLS:",
        strengths,
        "",
        "NEXT BEST ACTION:",
        f"  {summary['next_action_title'] or 'n/a'}",
        f"  kind={summary['next_action_kind'] or 'n/a'}",
        f"  dimension={summary['next_action_dimension'] or 'n/a'}",
        "",
        "WHY:",
        why,
    ]
    if summary["warnings"]:
        lines.append("")
        lines.append("WARNINGS:")
        lines.extend(f"  - {warning}" for warning in summary["warnings"])
    return "\n".join(lines)


def verify_demo_invariants(session: Session, summary: dict) -> None:
    if summary["attempts"] != summary["expected_attempts"]:
        raise DemoSeedError(
            f"Expected {summary['expected_attempts']} attempts, found {summary['attempts']}"
        )
    if summary["in_progress_attempts"] != 0:
        raise DemoSeedError("Demo user has in-progress attempts after seed.")
    if summary["evidence"] < 1:
        raise DemoSeedError("Demo seed produced no evidence.")
    if summary["snapshots"] < 1:
        raise DemoSeedError("Demo seed produced no snapshots.")
    if summary["recommendations"] < 1:
        raise DemoSeedError("Demo seed produced no recommendations.")
    if summary["target_name"] != "Product SDE":
        raise DemoSeedError("Demo seed did not select the Product SDE target.")
    if summary["dsa_assessed_count"] < MIN_DSA_ASSESSED_FOR_COVERAGE:
        raise DemoSeedError(
            "Demo seed assessed too few DSA skills "
            f"({summary['dsa_assessed_count']}); need at least {MIN_DSA_ASSESSED_FOR_COVERAGE} "
            "for the 40% coverage threshold."
        )
    coverage = summary["dsa_coverage"]
    if coverage is None or coverage < 0.40:
        raise DemoSeedError(f"DSA coverage is {coverage}; expected >= 0.40.")
    early_or_missing = {
        None,
        DimensionStatus.NOT_ASSESSED.value,
        DimensionStatus.EARLY.value,
    }
    if summary["dsa_status"] in early_or_missing:
        raise DemoSeedError(
            f"DSA remained {summary['dsa_status']} after seed; expected an assessed dimension."
        )
    if summary["dsa_score"] is None:
        raise DemoSeedError("DSA remains below the coverage threshold (no public score).")
    if summary["dsa_requirement"] not in {"meets", "exceeds"}:
        profile = ", ".join(
            f"{item.skill_slug}={item.status.value}:{item.score}:{item.evidence_count}"
            for item in summary["mastery"]
            if item.score is not None
        )
        raise DemoSeedError(
            f"DSA requirement status is {summary['dsa_requirement']} "
            f"(score={summary['dsa_score']}); expected meets or exceeds. {profile}"
        )
    if summary["core_cs_status"] != DimensionStatus.NOT_ASSESSED.value:
        raise DemoSeedError(f"Core CS should be not assessed, got {summary['core_cs_status']}.")
    if summary["core_cs_score"] is not None:
        raise DemoSeedError("Core CS unexpectedly has a public score on the initial demo seed.")
    for key in ("projects_status", "interview_status", "profile_status"):
        if summary[key] not in {DimensionStatus.NOT_ASSESSED.value, None}:
            raise DemoSeedError(f"{key} should be not assessed, got {summary[key]}.")
    if summary["next_action_kind"] != PlacementActionKind.ASSESS_DIMENSION.value:
        raise DemoSeedError(
            f"Next action kind is {summary['next_action_kind']}; expected assess_dimension."
        )
    if summary["next_action_dimension"] != ReadinessDimension.CORE_CS.value:
        raise DemoSeedError(
            f"Next action dimension is {summary['next_action_dimension']}; expected core_cs."
        )
    if summary["weakest_slug"] != "sliding-window":
        raise DemoSeedError(
            f"Weakest assessed DSA skill is {summary['weakest_slug']}; expected sliding-window."
        )
    if summary["strongest_slug"] != "arrays":
        raise DemoSeedError(
            f"Strongest assessed DSA skill is {summary['strongest_slug']}; expected arrays."
        )
    by_slug = {item.skill_slug: item for item in summary["mastery"]}
    window = by_slug.get("sliding-window")
    if window is None or window.status != MasteryStatus.ASSESSED or window.score is None:
        raise DemoSeedError("Sliding Window was not assessed by the real mastery engine.")
    if not (0.20 <= float(window.score) <= 0.60):
        raise DemoSeedError(
            f"Sliding Window score {window.score} is outside the intended weakness band."
        )
    for slug in (
        "arrays",
        "hashing",
        "two-pointers",
        "binary-search",
        "linked-lists",
        "trees",
        "sliding-window",
    ):
        skill = by_slug.get(slug)
        if skill is None or skill.status != MasteryStatus.ASSESSED or skill.score is None:
            raise DemoSeedError(f"{slug} was not assessed.")
        if float(skill.score) < 0.05:
            raise DemoSeedError(f"{slug} is assessed near 0%.")
    if summary["recommendation_state"] == STATE_COLD_START:
        raise DemoSeedError("Demo seed ended in cold-start despite attempt history.")
    if not summary["next_recommendation"]:
        raise DemoSeedError("Demo seed did not produce a next DSA recommendation.")
    for item in summary["mastery"]:
        if item.skill_slug in CORE_CS_SKILL_SLUGS and item.evidence_count > 0:
            raise DemoSeedError("Core CS evidence was created on the initial demo seed.")
        if item.status != MasteryStatus.ASSESSED:
            if item.score is not None:
                raise DemoSeedError(
                    f"Insufficient skill {item.skill_slug} unexpectedly has a public score."
                )
            continue
        if item.score is None:
            raise DemoSeedError(f"Assessed skill {item.skill_slug} has a null score.")
        if float(item.score) < 0.05 and float(item.confidence) >= 0.7:
            raise DemoSeedError(f"{item.skill_name} is assessed near 0% with high confidence.")
        if item.evidence_count < 1:
            raise DemoSeedError(f"Assessed skill {item.skill_slug} has no evidence.")
    demo_user = UserRepository().find_by_email(session, DEMO_EMAIL)
    assert demo_user is not None
    leaked = session.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.user_id != demo_user.id)
        .where(
            EvidenceItem.attempt_id.in_(select(Attempt.id).where(Attempt.user_id == demo_user.id))
        )
    )
    if leaked:
        raise DemoSeedError("Demo evidence is attached to the wrong user.")
    if summary["warnings"]:
        raise DemoSeedError("Demo seed produced warnings: " + "; ".join(summary["warnings"]))
