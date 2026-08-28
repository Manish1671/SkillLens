"""Initial domain schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

difficulty_enum = postgresql.ENUM("easy", "medium", "hard", name="difficulty", create_type=False)
attempt_status_enum = postgresql.ENUM(
    "in_progress",
    "submitted",
    "abandoned",
    name="attempt_status",
    create_type=False,
)
mistake_type_enum = postgresql.ENUM(
    "off_by_one",
    "wrong_data_structure",
    "missed_edge_case",
    "incorrect_complexity",
    "logic_error",
    "unknown",
    name="mistake_type",
    create_type=False,
)
attempt_event_type_enum = postgresql.ENUM(
    "started",
    "hint_revealed",
    "self_report",
    "submitted",
    "abandoned",
    name="attempt_event_type",
    create_type=False,
)
evidence_polarity_enum = postgresql.ENUM(
    "positive",
    "negative",
    "neutral",
    name="evidence_polarity",
    create_type=False,
)
mastery_status_enum = postgresql.ENUM(
    "insufficient",
    "assessed",
    name="mastery_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    difficulty_enum.create(bind, checkfirst=True)
    attempt_status_enum.create(bind, checkfirst=True)
    mistake_type_enum.create(bind, checkfirst=True)
    attempt_event_type_enum.create(bind, checkfirst=True)
    evidence_polarity_enum.create(bind, checkfirst=True)
    mastery_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "topics",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "problems",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("prompt_md", sa.Text(), nullable=False),
        sa.Column("difficulty", difficulty_enum, nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("solution_outline_md", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "skills",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_foundational", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "attempts",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("status", attempt_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column("hints_used_count", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("mistake_type", mistake_type_enum, nullable=True),
        sa.Column("code_text", sa.Text(), nullable=True),
        sa.Column("client_attempt_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "client_attempt_id", name="uq_attempts_user_client_attempt"),
    )
    op.create_index("ix_attempts_user_created_at", "attempts", ["user_id", "created_at"], unique=False)
    op.create_index("ix_attempts_user_problem", "attempts", ["user_id", "problem_id"], unique=False)
    op.create_index(
        "uq_attempts_user_problem_in_progress",
        "attempts",
        ["user_id", "problem_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )

    op.create_table(
        "hints",
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", "ordinal", name="uq_hints_problem_ordinal"),
    )

    op.create_table(
        "problem_skills",
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", "skill_id", name="uq_problem_skills_pair"),
    )

    op.create_table(
        "skill_dependencies",
        sa.Column("prerequisite_skill_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "prerequisite_skill_id != skill_id",
            name="ck_skill_dependencies_no_self",
        ),
        sa.ForeignKeyConstraint(["prerequisite_skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prerequisite_skill_id", "skill_id", name="uq_skill_dependencies_pair"),
    )
    op.create_index(
        "ix_skill_dependencies_prerequisite_skill_id",
        "skill_dependencies",
        ["prerequisite_skill_id"],
        unique=False,
    )
    op.create_index("ix_skill_dependencies_skill_id", "skill_dependencies", ["skill_id"], unique=False)

    op.create_table(
        "skill_masteries",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", mastery_status_enum, nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_skill_masteries_user_skill", "skill_masteries", ["user_id", "skill_id"], unique=True)

    op.create_table(
        "attempt_events",
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("event_type", attempt_event_type_enum, nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempt_events_attempt_id", "attempt_events", ["attempt_id"], unique=False)

    op.create_table(
        "evidence_items",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("polarity", evidence_polarity_enum, nullable=False),
        sa.Column("strength", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_items_user_skill_created",
        "evidence_items",
        ["user_id", "skill_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_evidence_items_attempt_id", "evidence_items", ["attempt_id"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("problem_id", sa.UUID(), nullable=False),
        sa.Column("target_skill_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source_attempt_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_attempt_id"], ["attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendations_user_generated",
        "recommendations",
        ["user_id", "generated_at"],
        unique=False,
    )

    op.create_table(
        "skill_assessment_snapshots",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_snapshots_user_skill_computed",
        "skill_assessment_snapshots",
        ["user_id", "skill_id", "computed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_snapshots_user_skill_computed", table_name="skill_assessment_snapshots")
    op.drop_table("skill_assessment_snapshots")

    op.drop_index("ix_recommendations_user_generated", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_evidence_items_attempt_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_user_skill_created", table_name="evidence_items")
    op.drop_table("evidence_items")

    op.drop_index("ix_attempt_events_attempt_id", table_name="attempt_events")
    op.drop_table("attempt_events")

    op.drop_index("uq_skill_masteries_user_skill", table_name="skill_masteries")
    op.drop_table("skill_masteries")

    op.drop_index("ix_skill_dependencies_skill_id", table_name="skill_dependencies")
    op.drop_index("ix_skill_dependencies_prerequisite_skill_id", table_name="skill_dependencies")
    op.drop_table("skill_dependencies")

    op.drop_table("problem_skills")
    op.drop_table("hints")

    op.drop_index("uq_attempts_user_problem_in_progress", table_name="attempts")
    op.drop_index("ix_attempts_user_problem", table_name="attempts")
    op.drop_index("ix_attempts_user_created_at", table_name="attempts")
    op.drop_table("attempts")

    op.drop_table("skills")
    op.drop_table("problems")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("topics")

    bind = op.get_bind()
    mastery_status_enum.drop(bind, checkfirst=True)
    evidence_polarity_enum.drop(bind, checkfirst=True)
    attempt_event_type_enum.drop(bind, checkfirst=True)
    mistake_type_enum.drop(bind, checkfirst=True)
    attempt_status_enum.drop(bind, checkfirst=True)
    difficulty_enum.drop(bind, checkfirst=True)
