"""Placement readiness tables.

Revision ID: 002_readiness
Revises: 001_initial
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_readiness"
down_revision: str | Sequence[str] | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIMENSIONS = ("dsa", "core_cs", "projects", "interview", "profile")
DIMENSION_SQL = ", ".join(f"'{value}'" for value in DIMENSIONS)


def upgrade() -> None:
    op.create_table(
        "target_profiles",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "target_requirements",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=True),
        sa.Column("min_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("min_confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("weight", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"dimension IN ({DIMENSION_SQL})",
            name="ck_target_requirements_dimension",
        ),
        sa.CheckConstraint(
            "min_score >= 0 AND min_score <= 1",
            name="ck_target_requirements_min_score",
        ),
        sa.CheckConstraint(
            "min_confidence >= 0 AND min_confidence <= 1",
            name="ck_target_requirements_min_confidence",
        ),
        sa.CheckConstraint("weight >= 0 AND weight <= 1", name="ck_target_requirements_weight"),
        sa.ForeignKeyConstraint(["profile_id"], ["target_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_target_requirements_profile_id",
        "target_requirements",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_target_requirements_skill_id",
        "target_requirements",
        ["skill_id"],
        unique=False,
    )
    op.create_index(
        "uq_target_requirements_profile_dimension",
        "target_requirements",
        ["profile_id", "dimension"],
        unique=True,
        postgresql_where=sa.text("skill_id IS NULL"),
    )
    op.create_index(
        "uq_target_requirements_profile_dimension_skill",
        "target_requirements",
        ["profile_id", "dimension", "skill_id"],
        unique=True,
        postgresql_where=sa.text("skill_id IS NOT NULL"),
    )
    op.create_table(
        "learner_targets",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column(
            "selected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["target_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_learner_targets_user"),
    )
    op.create_index("ix_learner_targets_profile_id", "learner_targets", ["profile_id"], unique=False)
    op.create_table(
        "dimension_skills",
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(f"dimension IN ({DIMENSION_SQL})", name="ck_dimension_skills_dimension"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dimension", "skill_id", name="uq_dimension_skills_dimension_skill"),
    )
    op.create_index("ix_dimension_skills_dimension", "dimension_skills", ["dimension"], unique=False)
    op.create_index("ix_dimension_skills_skill_id", "dimension_skills", ["skill_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dimension_skills_skill_id", table_name="dimension_skills")
    op.drop_index("ix_dimension_skills_dimension", table_name="dimension_skills")
    op.drop_table("dimension_skills")
    op.drop_index("ix_learner_targets_profile_id", table_name="learner_targets")
    op.drop_table("learner_targets")
    op.drop_index(
        "uq_target_requirements_profile_dimension_skill",
        table_name="target_requirements",
    )
    op.drop_index("uq_target_requirements_profile_dimension", table_name="target_requirements")
    op.drop_index("ix_target_requirements_skill_id", table_name="target_requirements")
    op.drop_index("ix_target_requirements_profile_id", table_name="target_requirements")
    op.drop_table("target_requirements")
    op.drop_table("target_profiles")
