from uuid import UUID

from app.models.problem import Problem, ProblemSkill
from app.models.skill import Skill, SkillDependency
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload


class SkillRepository:
    def list_all(self, session: Session) -> list[Skill]:
        return list(
            session.scalars(
                select(Skill)
                .options(
                    selectinload(Skill.prerequisite_edges),
                    selectinload(Skill.topic),
                )
                .order_by(Skill.sort_order, Skill.slug)
            ).all()
        )

    def find_by_slug(self, session: Session, slug: str) -> Skill | None:
        return session.scalar(
            select(Skill)
            .where(Skill.slug == slug)
            .options(
                selectinload(Skill.prerequisite_edges),
                selectinload(Skill.dependent_edges),
                selectinload(Skill.topic),
            )
        )

    def get_prerequisite_ids(self, session: Session, skill_id: UUID) -> list[UUID]:
        return list(
            session.scalars(
                select(SkillDependency.prerequisite_skill_id).where(
                    SkillDependency.skill_id == skill_id
                )
            ).all()
        )

    def find_linked_published_problems(self, session: Session, skill_id: UUID) -> list[Problem]:
        return list(
            session.scalars(
                select(Problem)
                .join(ProblemSkill)
                .where(
                    ProblemSkill.skill_id == skill_id,
                    Problem.is_published.is_(True),
                )
                .options(
                    selectinload(Problem.problem_skills).selectinload(ProblemSkill.skill),
                    selectinload(Problem.topic),
                )
                .order_by(Problem.slug)
            )
            .unique()
            .all()
        )

    def count_linked_published_problems(self, session: Session, skill_id: UUID) -> int:
        count = session.scalar(
            select(func.count())
            .select_from(Problem)
            .join(Problem.problem_skills)
            .where(
                ProblemSkill.skill_id == skill_id,
                Problem.is_published.is_(True),
            )
        )
        return int(count or 0)
