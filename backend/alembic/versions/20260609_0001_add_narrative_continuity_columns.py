from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260609_0001"
down_revision = None
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


def _add_json_column(table_name: str, column_name: str) -> None:
    if _has_table(table_name) and not _has_column(table_name, column_name):
        op.add_column(table_name, sa.Column(column_name, sa.JSON(), nullable=True))


def _add_column(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    for column_name in (
        "blueprint",
        "continuity_checks",
        "arc_step_refs",
        "continuity_from_previous",
        "state_delta",
        "continuity_to_next",
        "relationship_changes",
        "object_states",
        "external_pressures",
        "opening_requirements_for_next",
        "causality_links",
        "foreshadowing_tasks",
        "rhythm_profile",
    ):
        _add_json_column("chapters", column_name)

    for column_name in ("arc_continuity_index", "arc_bridge_checks"):
        _add_json_column("volumes", column_name)

    _add_json_column("characters", "current_state")
    _add_column("characters", sa.Column("first_appeared_chapter", sa.Integer(), nullable=True))
    _add_column("characters", sa.Column("first_appeared_title", sa.String(length=200), nullable=True))
    _add_column("characters", sa.Column("character_class", sa.String(length=20), nullable=True))

    for column_name in ("hard_rules", "tone_rules", "constraints"):
        _add_json_column("world_settings", column_name)


def downgrade() -> None:
    # Intentionally non-destructive for open-source user databases.
    pass
