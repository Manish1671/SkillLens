from decimal import Decimal
from uuid import UUID

from app.core.catalog_errors import NotFoundError
from app.core.enums import ActivityKind, ActivityKindQuery, Difficulty
from app.domain.quiz import public_quiz_options
from app.models.problem import Problem
from app.models.skill import Skill
from app.models.topic import Topic
from app.models.user import User
from app.repositories.problem_repository import LearnerProblemStateData, ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.catalog import (
    LearnerProblemState,
    ProblemDetailResponse,
    ProblemListItem,
    ProblemListResponse,
    ProblemSkillLink,
    QuizOptionPublic,
    SkillDetailResponse,
    SkillProblemSummary,
    SkillSummary,
    TopicSummary,
)
from sqlalchemy.orm import Session


class CatalogService:
    def __init__(
        self,
        topic_repository: TopicRepository,
        skill_repository: SkillRepository,
        problem_repository: ProblemRepository,
    ) -> None:
        self._topics = topic_repository
        self._skills = skill_repository
        self._problems = problem_repository

    def list_topics(self, session: Session) -> list[TopicSummary]:
        return [self._to_topic_summary(topic) for topic in self._topics.list_all(session)]

    def list_skills(self, session: Session) -> list[SkillSummary]:
        skills = self._skills.list_all(session)
        topic_by_id = {topic.id: topic for topic in self._topics.list_all(session)}
        return [self._to_skill_summary(skill, topic_by_id) for skill in skills]

    def get_skill_detail(self, session: Session, slug: str) -> SkillDetailResponse:
        skill = self._skills.find_by_slug(session, slug)
        if skill is None:
            raise NotFoundError(detail="Skill not found", code="skill_not_found")

        all_skills = self._skills.list_all(session)
        skills_by_id = {item.id: item for item in all_skills}
        topic_by_id = {topic.id: topic for topic in self._topics.list_all(session)}

        prerequisites = [
            self._to_skill_summary(skills_by_id[edge.prerequisite_skill_id], topic_by_id)
            for edge in skill.prerequisite_edges
            if edge.prerequisite_skill_id in skills_by_id
        ]
        dependents = [
            self._to_skill_summary(skills_by_id[edge.skill_id], topic_by_id)
            for edge in skill.dependent_edges
            if edge.skill_id in skills_by_id
        ]
        linked_problems = [
            SkillProblemSummary(
                slug=problem.slug,
                title=problem.title,
                difficulty=problem.difficulty,
                estimated_minutes=problem.estimated_minutes,
                activity_kind=problem.activity_kind,
            )
            for problem in self._skills.find_linked_published_problems(session, skill.id)
        ]

        topic_slug = None
        if skill.topic_id and skill.topic_id in topic_by_id:
            topic_slug = topic_by_id[skill.topic_id].slug

        return SkillDetailResponse(
            slug=skill.slug,
            name=skill.name,
            description=skill.description,
            topic_slug=topic_slug,
            is_foundational=skill.is_foundational,
            sort_order=skill.sort_order,
            prerequisites=prerequisites,
            dependents=dependents,
            linked_problems=linked_problems,
        )

    def list_problems(
        self,
        session: Session,
        *,
        topic: str | None = None,
        skill: str | None = None,
        difficulty: Difficulty | None = None,
        activity_kind: ActivityKindQuery = ActivityKindQuery.CODING,
        search_query: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
        current_user: User | None = None,
    ) -> ProblemListResponse:
        kind_filter = None
        if activity_kind == ActivityKindQuery.CODING:
            kind_filter = ActivityKind.CODING
        elif activity_kind == ActivityKindQuery.QUIZ:
            kind_filter = ActivityKind.QUIZ
        problems, has_more = self._problems.list_published(
            session,
            topic_slug=topic,
            skill_slug=skill,
            difficulty=difficulty,
            activity_kind=kind_filter,
            search_query=search_query,
            cursor=cursor,
            limit=limit,
        )
        learner_states = self._learner_states_for_problems(session, current_user, problems)
        next_cursor = problems[-1].slug if has_more and problems else None
        return ProblemListResponse(
            items=[
                self._to_problem_list_item(problem, learner_states.get(problem.id))
                for problem in problems
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_problem_detail(
        self,
        session: Session,
        slug: str,
        current_user: User | None = None,
    ) -> ProblemDetailResponse:
        problem = self._problems.find_published_by_slug(session, slug)
        if problem is None:
            raise NotFoundError(detail="Problem not found", code="problem_not_found")

        learner_states = self._learner_states_for_problems(session, current_user, [problem])
        hint_count = (
            len(problem.hints) if problem.hints else self._problems.count_hints(session, problem.id)
        )

        return ProblemDetailResponse(
            id=str(problem.id),
            slug=problem.slug,
            title=problem.title,
            prompt_md=problem.prompt_md,
            difficulty=problem.difficulty,
            estimated_minutes=problem.estimated_minutes,
            activity_kind=problem.activity_kind,
            topic=self._to_topic_summary(problem.topic),
            skills=self._to_problem_skills(problem),
            hint_count=hint_count,
            options=self._public_quiz_options(problem),
            learner_state=self._to_learner_state(learner_states.get(problem.id)),
        )

    def _learner_states_for_problems(
        self,
        session: Session,
        current_user: User | None,
        problems: list[Problem],
    ) -> dict[UUID, LearnerProblemState | None]:
        if current_user is None or not problems:
            return {}
        raw = self._problems.get_learner_states(
            session,
            current_user.id,
            [problem.id for problem in problems],
        )
        return {problem_id: self._to_learner_state(state) for problem_id, state in raw.items()}

    def _to_topic_summary(self, topic: Topic) -> TopicSummary:
        return TopicSummary(slug=topic.slug, name=topic.name, sort_order=topic.sort_order)

    def _to_skill_summary(
        self,
        skill: Skill,
        topic_by_id: dict[UUID, Topic],
    ) -> SkillSummary:
        prerequisite_ids = [str(edge.prerequisite_skill_id) for edge in skill.prerequisite_edges]
        topic_slug = None
        if skill.topic_id and skill.topic_id in topic_by_id:
            topic_slug = topic_by_id[skill.topic_id].slug
        return SkillSummary(
            slug=skill.slug,
            name=skill.name,
            description=skill.description,
            topic_slug=topic_slug,
            is_foundational=skill.is_foundational,
            sort_order=skill.sort_order,
            prerequisite_skill_ids=prerequisite_ids,
        )

    def _to_problem_skills(self, problem: Problem) -> list[ProblemSkillLink]:
        links: list[ProblemSkillLink] = []
        for link in problem.problem_skills:
            links.append(
                ProblemSkillLink(
                    slug=link.skill.slug,
                    name=link.skill.name,
                    weight=link.weight,
                    is_primary=link.weight >= Decimal("1.0"),
                )
            )
        links.sort(key=lambda item: (-float(item.weight), item.slug))
        return links

    def _to_problem_list_item(
        self,
        problem: Problem,
        learner_state: LearnerProblemState | None,
    ) -> ProblemListItem:
        return ProblemListItem(
            id=str(problem.id),
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            estimated_minutes=problem.estimated_minutes,
            activity_kind=problem.activity_kind,
            topic=self._to_topic_summary(problem.topic),
            skills=self._to_problem_skills(problem),
            learner_state=learner_state,
        )

    def _public_quiz_options(self, problem: Problem) -> list[QuizOptionPublic] | None:
        if problem.activity_kind != ActivityKind.QUIZ:
            return None
        return [
            QuizOptionPublic(id=item["id"], label=item["label"])
            for item in public_quiz_options(problem.quiz_spec)
        ]

    def _to_learner_state(
        self, state: LearnerProblemStateData | LearnerProblemState | None
    ) -> LearnerProblemState | None:
        if state is None:
            return None
        if isinstance(state, LearnerProblemState):
            return state
        return LearnerProblemState(
            attempted=state.attempted,
            solved=state.solved,
            in_progress=state.in_progress,
        )
