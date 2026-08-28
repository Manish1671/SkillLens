from dataclasses import dataclass
from uuid import UUID

from app.core.enums import ActivityKind, AttemptStatus, Difficulty
from app.models.attempt import Attempt
from app.models.problem import Hint, Problem, ProblemSkill
from app.models.skill import Skill
from app.models.topic import Topic
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload


@dataclass
class LearnerProblemStateData:
    attempted: bool
    solved: bool
    in_progress: bool


class ProblemRepository:
    def list_published(
        self,
        session: Session,
        *,
        topic_slug: str | None = None,
        skill_slug: str | None = None,
        difficulty: Difficulty | None = None,
        activity_kind: ActivityKind | None = None,
        search_query: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Problem], bool]:
        stmt = (
            select(Problem)
            .where(Problem.is_published.is_(True))
            .options(
                selectinload(Problem.topic),
                selectinload(Problem.problem_skills).selectinload(ProblemSkill.skill),
            )
        )

        if topic_slug:
            stmt = stmt.join(Problem.topic).where(Topic.slug == topic_slug)

        if skill_slug:
            stmt = (
                stmt.join(Problem.problem_skills)
                .join(ProblemSkill.skill)
                .where(Skill.slug == skill_slug)
            )

        if difficulty is not None:
            stmt = stmt.where(Problem.difficulty == difficulty)

        if activity_kind is not None:
            stmt = stmt.where(Problem.activity_kind == activity_kind)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            stmt = stmt.where(or_(Problem.title.ilike(pattern), Problem.slug.ilike(pattern)))

        if cursor:
            stmt = stmt.where(Problem.slug > cursor)

        stmt = stmt.order_by(Problem.slug).limit(limit + 1)
        problems = list(session.scalars(stmt).unique().all())
        has_more = len(problems) > limit
        if has_more:
            problems = problems[:limit]
        return problems, has_more

    def find_published_by_slug(self, session: Session, slug: str) -> Problem | None:
        return session.scalar(
            select(Problem)
            .where(Problem.slug == slug, Problem.is_published.is_(True))
            .options(
                selectinload(Problem.topic),
                selectinload(Problem.problem_skills).selectinload(ProblemSkill.skill),
                selectinload(Problem.hints),
            )
        )

    def find_published_by_id(self, session: Session, problem_id: UUID) -> Problem | None:
        return session.scalar(
            select(Problem)
            .where(Problem.id == problem_id, Problem.is_published.is_(True))
            .options(
                selectinload(Problem.hints),
                selectinload(Problem.problem_skills).selectinload(ProblemSkill.skill),
            )
        )

    def find_hint_for_problem(
        self, session: Session, problem_id: UUID, hint_id: UUID
    ) -> Hint | None:
        return session.scalar(select(Hint).where(Hint.id == hint_id, Hint.problem_id == problem_id))

    def count_hints(self, session: Session, problem_id: UUID) -> int:
        count = session.scalar(
            select(func.count()).select_from(Hint).where(Hint.problem_id == problem_id)
        )
        return int(count or 0)

    def get_learner_states(
        self,
        session: Session,
        user_id: UUID,
        problem_ids: list[UUID],
    ) -> dict[UUID, LearnerProblemStateData]:
        if not problem_ids:
            return {}

        attempts = session.scalars(
            select(Attempt).where(
                Attempt.user_id == user_id,
                Attempt.problem_id.in_(problem_ids),
            )
        ).all()

        states: dict[UUID, LearnerProblemStateData] = {}
        for attempt in attempts:
            current = states.get(
                attempt.problem_id,
                LearnerProblemStateData(attempted=False, solved=False, in_progress=False),
            )
            current.attempted = True
            if attempt.status == AttemptStatus.IN_PROGRESS:
                current.in_progress = True
            if attempt.status == AttemptStatus.SUBMITTED and attempt.is_correct:
                current.solved = True
            states[attempt.problem_id] = current
        return states
