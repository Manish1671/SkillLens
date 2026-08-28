from app.core.enums import ReadinessDimension

TARGET_PROFILE_DISCLAIMER = (
    "SkillLens target profiles are internal readiness models, not official "
    "company hiring requirements."
)

TARGET_PROFILES = [
    {
        "slug": "product-sde",
        "name": "Product SDE",
        "description": (
            "SkillLens's configurable baseline for product-oriented software "
            "engineering placement preparation."
        ),
        "is_system": True,
        "sort_order": 10,
        "requirements": [
            {
                "dimension": ReadinessDimension.DSA.value,
                "skill_slug": None,
                "min_score": "0.7000",
                "min_confidence": "0.5500",
                "weight": "0.4000",
                "is_critical": True,
            },
            {
                "dimension": ReadinessDimension.CORE_CS.value,
                "skill_slug": None,
                "min_score": "0.6000",
                "min_confidence": "0.5000",
                "weight": "0.3500",
                "is_critical": True,
            },
        ],
    }
]
