from collections import defaultdict
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.enums import ActivityKind
from app.models import Hint, Problem, ProblemSkill, Skill, SkillDependency, Topic
from app.models.readiness import DimensionSkill, TargetProfile, TargetRequirement
from app.seed.core_cs_data import (
    CORE_CS_DEPENDENCIES,
    CORE_CS_PROBLEMS,
    CORE_CS_SKILL_SLUGS,
    CORE_CS_SKILLS,
    CORE_CS_TOPIC,
)
from app.seed.data import PROBLEMS, SKILL_DEPENDENCIES, SKILLS, TOPICS
from app.seed.readiness_data import TARGET_PROFILES

ALL_TOPICS = [*TOPICS, CORE_CS_TOPIC]
ALL_SKILLS = [*SKILLS, *CORE_CS_SKILLS]
ALL_PROBLEMS = [*PROBLEMS, *CORE_CS_PROBLEMS]
ALL_DEPENDENCIES = [*SKILL_DEPENDENCIES, *CORE_CS_DEPENDENCIES]


def validate_skill_graph_is_acyclic(dependencies: list[tuple[str, str]]) -> None:
    graph: dict[str, list[str]] = defaultdict(list)
    for prereq, skill in dependencies:
        if prereq == skill:
            raise ValueError(f"Self dependency detected for skill '{skill}'")
        graph[prereq].append(skill)

    visited: set[str] = set()
    visiting: set[str] = set()

    def dfs(node: str) -> None:
        if node in visiting:
            raise ValueError(f"Cycle detected involving skill '{node}'")
        if node in visited:
            return
        visiting.add(node)
        for neighbor in graph[node]:
            dfs(neighbor)
        visiting.remove(node)
        visited.add(node)

    nodes = set(graph.keys())
    for neighbor_list in graph.values():
        nodes.update(neighbor_list)
    for node in nodes:
        dfs(node)


def clear_catalog(session: Session) -> None:
    session.execute(delete(DimensionSkill))
    session.execute(delete(TargetRequirement).where(TargetRequirement.skill_id.is_not(None)))
    session.execute(delete(Hint))
    session.execute(delete(ProblemSkill))
    session.execute(delete(Problem))
    session.execute(delete(SkillDependency))
    session.execute(delete(Skill))
    session.execute(delete(Topic))


def seed_catalog(session: Session, commit: bool = True) -> dict[str, int]:
    validate_skill_graph_is_acyclic(ALL_DEPENDENCIES)

    clear_catalog(session)

    topic_by_slug: dict[str, Topic] = {}
    for topic_data in ALL_TOPICS:
        topic = Topic(
            slug=topic_data["slug"],
            name=topic_data["name"],
            sort_order=topic_data["sort_order"],
        )
        session.add(topic)
        topic_by_slug[topic.slug] = topic
    session.flush()

    skill_by_slug: dict[str, Skill] = {}
    for skill_data in ALL_SKILLS:
        skill = Skill(
            slug=skill_data["slug"],
            name=skill_data["name"],
            topic_id=topic_by_slug[skill_data["topic_slug"]].id,
            description=skill_data["description"],
            is_foundational=skill_data["is_foundational"],
            sort_order=skill_data["sort_order"],
        )
        session.add(skill)
        skill_by_slug[skill.slug] = skill
    session.flush()

    for prereq_slug, skill_slug in ALL_DEPENDENCIES:
        session.add(
            SkillDependency(
                prerequisite_skill_id=skill_by_slug[prereq_slug].id,
                skill_id=skill_by_slug[skill_slug].id,
            )
        )

    for problem_data in ALL_PROBLEMS:
        activity_kind = problem_data.get("activity_kind", ActivityKind.CODING)
        problem = Problem(
            slug=problem_data["slug"],
            title=problem_data["title"],
            prompt_md=problem_data["prompt_md"],
            difficulty=problem_data["difficulty"],
            estimated_minutes=problem_data["estimated_minutes"],
            topic_id=topic_by_slug[problem_data["topic_slug"]].id,
            is_published=True,
            solution_outline_md=problem_data["solution_outline_md"],
            activity_kind=activity_kind,
            quiz_spec=problem_data.get("quiz_spec"),
        )
        session.add(problem)
        session.flush()

        for skill_link in problem_data["skills"]:
            session.add(
                ProblemSkill(
                    problem_id=problem.id,
                    skill_id=skill_by_slug[skill_link["skill_slug"]].id,
                    weight=Decimal(str(skill_link["weight"])),
                )
            )

        for ordinal, hint_body in enumerate(problem_data["hints"], start=1):
            session.add(
                Hint(
                    problem_id=problem.id,
                    ordinal=ordinal,
                    body_md=hint_body,
                )
            )

    session.flush()

    seed_readiness_config(session, skill_by_slug)

    if commit:
        session.commit()

    return {
        "topics": session.scalar(select(func.count()).select_from(Topic)) or 0,
        "skills": session.scalar(select(func.count()).select_from(Skill)) or 0,
        "problems": session.scalar(select(func.count()).select_from(Problem)) or 0,
        "dependencies": session.scalar(select(func.count()).select_from(SkillDependency)) or 0,
        "hints": session.scalar(select(func.count()).select_from(Hint)) or 0,
        "target_profiles": session.scalar(select(func.count()).select_from(TargetProfile)) or 0,
        "dimension_skills": session.scalar(select(func.count()).select_from(DimensionSkill)) or 0,
    }


def seed_readiness_config(session: Session, skill_by_slug: dict[str, Skill]) -> None:
    session.execute(delete(DimensionSkill))
    core_cs = set(CORE_CS_SKILL_SLUGS)
    for skill in skill_by_slug.values():
        dimension = "core_cs" if skill.slug in core_cs else "dsa"
        session.add(DimensionSkill(dimension=dimension, skill_id=skill.id))
    session.flush()

    for profile_data in TARGET_PROFILES:
        profile = session.scalar(
            select(TargetProfile).where(TargetProfile.slug == profile_data["slug"])
        )
        if profile is None:
            profile = TargetProfile(
                slug=profile_data["slug"],
                name=profile_data["name"],
                description=profile_data["description"],
                is_system=profile_data["is_system"],
                sort_order=profile_data["sort_order"],
            )
            session.add(profile)
            session.flush()
        else:
            profile.name = profile_data["name"]
            profile.description = profile_data["description"]
            profile.is_system = profile_data["is_system"]
            profile.sort_order = profile_data["sort_order"]
            session.execute(
                delete(TargetRequirement).where(TargetRequirement.profile_id == profile.id)
            )
            session.flush()

        for requirement in profile_data["requirements"]:
            skill_slug = requirement["skill_slug"]
            skill_id = skill_by_slug[skill_slug].id if skill_slug else None
            session.add(
                TargetRequirement(
                    profile_id=profile.id,
                    dimension=requirement["dimension"],
                    skill_id=skill_id,
                    min_score=Decimal(requirement["min_score"]),
                    min_confidence=Decimal(requirement["min_confidence"]),
                    weight=Decimal(requirement["weight"]),
                    is_critical=requirement["is_critical"],
                )
            )
    session.flush()


def run_seed(session: Session, commit: bool = True) -> dict[str, int]:
    return seed_catalog(session, commit=commit)
