from app.repositories.assessment_repository import (
    EvidenceRepository,
    MasteryRepository,
    RecommendationRepository,
    SnapshotRepository,
)
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.placement_action_repository import PlacementActionRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.readiness_repository import (
    DimensionSkillRepository,
    LearnerTargetRepository,
    TargetProfileRepository,
)
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.services.assessment_plan_service import AssessmentPlanService
from app.services.assessment_service import AssessmentService
from app.services.attempt_service import AttemptService
from app.services.placement_action_service import PlacementActionService
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService

_evidence_repository = EvidenceRepository()
_mastery_repository = MasteryRepository()
_snapshot_repository = SnapshotRepository()
_recommendation_repository = RecommendationRepository()
_skill_repository = SkillRepository()
_problem_repository = ProblemRepository()
_topic_repository = TopicRepository()
_attempt_repository = AttemptRepository()
_target_profile_repository = TargetProfileRepository()
_learner_target_repository = LearnerTargetRepository()
_dimension_skill_repository = DimensionSkillRepository()
_placement_action_repository = PlacementActionRepository()

recommendation_service = RecommendationService(
    _recommendation_repository,
    _mastery_repository,
    _skill_repository,
    _problem_repository,
    _attempt_repository,
    _topic_repository,
)

assessment_service = AssessmentService(
    _evidence_repository,
    _mastery_repository,
    _snapshot_repository,
    _skill_repository,
    _problem_repository,
    _topic_repository,
    recommendation_service,
)

readiness_service = ReadinessService(
    _target_profile_repository,
    _learner_target_repository,
    _dimension_skill_repository,
    _mastery_repository,
    _skill_repository,
)

assessment_plan_service = AssessmentPlanService(
    readiness_service,
    _skill_repository,
    _problem_repository,
    _mastery_repository,
    _dimension_skill_repository,
)

placement_action_service = PlacementActionService(
    _placement_action_repository,
    readiness_service,
    recommendation_service,
    _mastery_repository,
    _skill_repository,
    _problem_repository,
    _attempt_repository,
)

attempt_service = AttemptService(
    _attempt_repository,
    _problem_repository,
    assessment_service,
    placement_action_service,
)
