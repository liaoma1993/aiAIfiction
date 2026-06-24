from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260623_0004"
down_revision = "20260610_0003"
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
    if _has_table("projects"):
        if not _has_column("projects", "master_outline"):
            op.add_column(
                "projects",
                sa.Column("master_outline", sa.Text(), nullable=False, server_default=""),
            )
        if not _has_column("projects", "pending_volume_plan"):
            op.add_column(
                "projects",
                sa.Column("pending_volume_plan", sa.JSON(), nullable=True),
            )


def downgrade() -> None:
    # Intentionally non-destructive: data preserved for safety.
    pass
