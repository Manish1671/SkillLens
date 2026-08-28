from dataclasses import dataclass

from app.core.enums import MistakeType

DEMO_EMAIL = "demo@skilllens.local"
DEMO_DISPLAY_NAME = "Alex"
DEMO_PASSWORD_ENV = "SKILLENS_DEMO_PASSWORD"

DSA_IN_SCOPE_COUNT = 14
MIN_DSA_ASSESSED_FOR_COVERAGE = 6


@dataclass(frozen=True)
class DemoAttemptSpec:
    """One historical attempt. Outcomes go through AttemptService → AssessmentService."""

    client_attempt_id: str
    problem_slug: str
    is_correct: bool
    hint_count: int
    time_spent_seconds: int
    days_ago: int
    hour: int
    minute: int
    mistake_type: MistakeType | None = None


# Oldest → newest. Three primary successes are required to cross the 1.5
# effective-evidence assessed threshold after recency decay.
#
# Seven assessed DSA skills (7/14 = 50% coverage). Sliding Window fails are
# older so recency decay limits their pull on the evidence-weighted DSA mean.
# Later Sliding Window successes keep the skill assessed and off 0%.
# hint_reliance is on a one-off DP solve so it does not drag assessed DSA scores.
DEMO_ATTEMPTS: tuple[DemoAttemptSpec, ...] = (
    # Foundation
    DemoAttemptSpec("demo-01", "max-profit-single-trade", True, 0, 410, 20, 2, 12),
    DemoAttemptSpec("demo-02", "contains-duplicate", True, 0, 155, 19, 3, 40),
    DemoAttemptSpec("demo-03", "classic-binary-search", True, 0, 230, 18, 1, 18),
    DemoAttemptSpec("demo-04", "reverse-linked-list", True, 0, 360, 17, 4, 5),
    DemoAttemptSpec("demo-05", "max-tree-depth", True, 0, 240, 16, 3, 10),
    # Sliding Window struggle (early, so negative evidence decays)
    DemoAttemptSpec(
        "demo-06",
        "longest-unique-substring",
        False,
        0,
        890,
        15,
        5,
        10,
        MistakeType.MISSED_EDGE_CASE,
    ),
    DemoAttemptSpec(
        "demo-07",
        "longest-unique-substring",
        False,
        1,
        710,
        14,
        6,
        42,
        MistakeType.LOGIC_ERROR,
    ),
    # Development
    DemoAttemptSpec("demo-08", "max-profit-single-trade", True, 0, 280, 13, 2, 50),
    DemoAttemptSpec("demo-09", "pair-sum-lookup", True, 0, 320, 12, 3, 22),
    DemoAttemptSpec("demo-10", "sorted-pair-sum", True, 0, 760, 12, 1, 33),
    DemoAttemptSpec("demo-11", "search-rotated-array", True, 0, 940, 11, 4, 8),
    DemoAttemptSpec("demo-12", "reverse-linked-list", True, 0, 300, 10, 1, 20),
    DemoAttemptSpec("demo-13", "max-tree-depth", True, 0, 200, 10, 2, 8),
    DemoAttemptSpec("demo-14", "contains-duplicate", True, 0, 180, 9, 2, 15),
    # Sliding Window partial recovery + DP hint_reliance (DP stays unassessed)
    DemoAttemptSpec("demo-15", "min-subarray-sum-target", True, 1, 1180, 8, 2, 15),
    DemoAttemptSpec("demo-16", "climbing-stairs", True, 2, 420, 8, 4, 40),
    DemoAttemptSpec("demo-17", "classic-binary-search", True, 0, 195, 7, 3, 5),
    DemoAttemptSpec("demo-18", "sorted-pair-sum", True, 0, 680, 6, 4, 16),
    DemoAttemptSpec("demo-19", "min-subarray-sum-target", True, 0, 990, 5, 2, 8),
    DemoAttemptSpec("demo-20", "max-tree-depth", True, 0, 180, 4, 3, 40),
    DemoAttemptSpec("demo-21", "reverse-linked-list", True, 0, 280, 3, 1, 20),
    DemoAttemptSpec(
        "demo-22",
        "valid-parentheses",
        False,
        0,
        260,
        3,
        2,
        18,
        MistakeType.LOGIC_ERROR,
    ),
    # Recent volume on strong skills to lift the evidence-weighted DSA mean
    DemoAttemptSpec("demo-23", "max-profit-single-trade", True, 0, 250, 2, 1, 28),
    DemoAttemptSpec("demo-24", "contains-duplicate", True, 0, 140, 2, 4, 5),
    DemoAttemptSpec("demo-25", "three-sum-zero", True, 0, 1280, 1, 4, 55),
    DemoAttemptSpec("demo-26", "search-rotated-array", True, 0, 860, 1, 3, 12),
    DemoAttemptSpec("demo-27", "max-profit-single-trade", True, 0, 220, 1, 5, 10),
    DemoAttemptSpec("demo-28", "max-profit-single-trade", True, 0, 210, 1, 5, 40),
    DemoAttemptSpec("demo-29", "min-subarray-sum-target", True, 0, 840, 1, 6, 20),
    DemoAttemptSpec("demo-30", "min-subarray-sum-target", True, 0, 800, 1, 6, 50),
    DemoAttemptSpec("demo-31", "max-profit-single-trade", True, 0, 200, 1, 7, 5),
    DemoAttemptSpec("demo-32", "max-profit-single-trade", True, 0, 195, 1, 7, 25),
    DemoAttemptSpec("demo-33", "pair-sum-lookup", True, 0, 280, 1, 8, 10),
)
