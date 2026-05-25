"""export_task

创建 export_task 表，用于跟踪异步导出任务。
含精细化增强：
  - 自动更新 updated_at 的数据库触发器
  - 关键业务字段的列注释
  - 精简索引（移除 PostgreSQL 主键自动索引的冗余声明）

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24 20:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_comments() -> None:
    """为导出相关字段添加数据库注释"""
    comments = {
        ("export_task", "format"): "导出格式：txt / epub / html / docx",
        ("export_task", "status"): "任务状态：pending / processing / completed / failed",
        ("export_task", "include_options"): "导出选项：{include_outline, include_characters, include_notes}",
        ("export_task", "chapter_ids"): "指定导出的章节 ID 列表，null 表示导出全部",
        ("export_task", "file_path"): "MinIO 中的文件存储路径",
        ("export_task", "file_size"): "文件大小（字节）",
        ("export_task", "download_url"): "预签名下载链接（有效期较短）",
    }
    for (table, column), comment in comments.items():
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{comment}';")


def upgrade() -> None:
    # ================================================================
    # 16. export_task（FK → project, user）
    # ================================================================
    op.create_table(
        "export_task",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column(
            "include_options",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("chapter_ids", postgresql.JSONB, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("download_url", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
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
    op.create_index("idx_export_task_project_id", "export_task", ["project_id"])
    op.create_index("idx_export_task_status", "export_task", ["status"])
    op.create_index("idx_export_task_user_id", "export_task", ["user_id"])

    # ── 增强 ─────────────────────────────────────────────────────────
    # updated_at 触发器（复用 0001 中定义的公共函数）
    op.execute("""
        CREATE TRIGGER trg_export_task_updated_at
            BEFORE UPDATE ON export_task
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    _add_column_comments()


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_export_task_updated_at ON export_task;")
    op.drop_index("idx_export_task_user_id", table_name="export_task")
    op.drop_index("idx_export_task_status", table_name="export_task")
    op.drop_index("idx_export_task_project_id", table_name="export_task")
    op.drop_table("export_task")
