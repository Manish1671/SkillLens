"""Quiz activity kind and server-side quiz spec.

Revision ID: 003_quiz_activity
Revises: 002_readiness
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_quiz_activity"
down_revision: str | Sequence[str] | None = "002_readiness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

activity_kind_enum = postgresql.ENUM("coding", "quiz", name="activity_kind", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    activity_kind_enum.create(bind, checkfirst=True)
    op.add_column(
        "problems",
        sa.Column(
            "activity_kind",
            activity_kind_enum,
            nullable=False,
            server_default="coding",
        ),
    )
    op.add_column(
        "problems",
        sa.Column("quiz_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_problems_activity_kind", "problems", ["activity_kind"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_problems_activity_kind", table_name="problems")
    op.drop_column("problems", "quiz_spec")
    op.drop_column("problems", "activity_kind")
    bind = op.get_bind()
    activity_kind_enum.drop(bind, checkfirst=True)
