from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260623_0005"
down_revision = "20260623_0004"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(table_name):
        return False
    return column_name in {col["name"] for col in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if _has_table("project_plan_sessions") and not _has_column("project_plan_sessions", "rejected_entries"):
        op.add_column(
            "project_plan_sessions",
            sa.Column("rejected_entries", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    # Intentionally non-destructive: data preserved for safety.
    pass
