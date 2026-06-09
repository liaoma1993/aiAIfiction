from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260609_0002"
down_revision = "20260609_0001"
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


def _add_column(column: sa.Column) -> None:
    if _has_table("projects") and not _has_column("projects", column.name):
        op.add_column("projects", column)


def upgrade() -> None:
    _add_column(sa.Column("project_schema_mode", sa.String(length=30), nullable=True))
    _add_column(sa.Column("arc_generation_version", sa.String(length=30), nullable=True))
    _add_column(sa.Column("chapter_blueprint_version", sa.String(length=30), nullable=True))
    _add_column(sa.Column("continuity_upgrade_notes", sa.JSON(), nullable=True))

    if _has_table("projects"):
        op.execute(
            "UPDATE projects SET "
            "project_schema_mode = COALESCE(project_schema_mode, 'legacy'), "
            "arc_generation_version = COALESCE(arc_generation_version, 'legacy'), "
            "chapter_blueprint_version = COALESCE(chapter_blueprint_version, 'legacy')"
        )


def downgrade() -> None:
    # Intentionally non-destructive for open-source user databases.
    pass
