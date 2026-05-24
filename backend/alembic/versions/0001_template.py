"""add template table

Revision ID: 0001_template
Revises:
Create Date: 2026-05-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_template"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "template",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            index=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "source_project_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("target_length", sa.String(20), nullable=False),
        sa.Column(
            "writing_style",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("story_brief", sa.Text, nullable=True),
        sa.Column(
            "world_setting",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "characters",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "usage_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_template_user_id", "template", ["user_id"])
    op.create_index("idx_template_genre", "template", ["genre"])


def downgrade() -> None:
    op.drop_index("idx_template_genre", table_name="template")
    op.drop_index("idx_template_user_id", table_name="template")
    op.drop_table("template")
