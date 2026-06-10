from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260610_0003"
down_revision = "20260609_0002"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    if not _has_table(table_name):
        return False
    return index_name in {idx["name"] for idx in sa.inspect(bind).get_indexes(table_name)}


def _create_index(index_name: str, column_name: str) -> None:
    if _has_table("llm_call_logs") and not _has_index("llm_call_logs", index_name):
        op.create_index(index_name, "llm_call_logs", [column_name])


def upgrade() -> None:
    if not _has_table("llm_call_logs"):
        op.create_table(
            "llm_call_logs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_name", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("task_id", sa.String(length=36), nullable=False, server_default=""),
            sa.Column("function_name", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("provider_id", sa.String(length=36), nullable=False, server_default=""),
            sa.Column("provider_name", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("provider_type", sa.String(length=30), nullable=False, server_default=""),
            sa.Column("model_name", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("request_type", sa.String(length=30), nullable=False, server_default="chat"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
            sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
            sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
            sa.Column("response_content", sa.Text(), nullable=False, server_default=""),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("temperature", sa.String(length=20), nullable=False, server_default=""),
            sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("request_payload", sa.JSON(), nullable=True),
            sa.Column("response_metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    for index_name, column_name in (
        ("ix_llm_call_logs_project_id", "project_id"),
        ("ix_llm_call_logs_project_name", "project_name"),
        ("ix_llm_call_logs_task_id", "task_id"),
        ("ix_llm_call_logs_function_name", "function_name"),
        ("ix_llm_call_logs_model_name", "model_name"),
        ("ix_llm_call_logs_status", "status"),
        ("ix_llm_call_logs_created_at", "created_at"),
    ):
        _create_index(index_name, column_name)


def downgrade() -> None:
    # Intentionally non-destructive for user audit history.
    pass
