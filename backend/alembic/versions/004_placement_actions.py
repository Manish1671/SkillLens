"""Placement actions table.

Revision ID: 004_placement_actions
Revises: 003_quiz_activity
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_placement_actions"
down_revision: str | Sequence[str] | None = "003_quiz_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTION_KINDS = ("dsa_problem", "cs_quiz", "assess_dimension")
ACTION_SQL = ", ".join(f"'{value}'" for value in ACTION_KINDS)
DIMENSIONS = ("dsa", "core_cs", "projects", "interview", "profile")
DIMENSION_SQL = ", ".join(f"'{value}'" for value in DIMENSIONS)


def upgrade() -> None:
    op.create_table(
        "placement_actions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("action_kind", sa.String(length=32), nullable=False),
        sa.Column("target_dimension", sa.String(length=32), nullable=False),
        sa.Column("target_skill_id", sa.UUID(), nullable=True),
        sa.Column("problem_id", sa.UUID(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_attempt_id", sa.UUID(), nullable=True),
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
            f"action_kind IN ({ACTION_SQL})",
            name="ck_placement_actions_action_kind",
        ),
        sa.CheckConstraint(
            f"target_dimension IN ({DIMENSION_SQL})",
            name="ck_placement_actions_target_dimension",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_attempt_id"], ["attempts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_placement_actions_user_generated",
        "placement_actions",
        ["user_id", "generated_at"],
    )
    op.create_index(
        "ix_placement_actions_user_rank",
        "placement_actions",
        ["user_id", "generated_at", "rank"],
    )
    op.create_index(
        "ix_placement_actions_target_skill_id",
        "placement_actions",
        ["target_skill_id"],
    )
    op.create_index("ix_placement_actions_problem_id", "placement_actions", ["problem_id"])


def downgrade() -> None:
    op.drop_index("ix_placement_actions_problem_id", table_name="placement_actions")
    op.drop_index("ix_placement_actions_target_skill_id", table_name="placement_actions")
    op.drop_index("ix_placement_actions_user_rank", table_name="placement_actions")
    op.drop_index("ix_placement_actions_user_generated", table_name="placement_actions")
    op.drop_table("placement_actions")
