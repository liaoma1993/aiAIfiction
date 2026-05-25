"""initial_schema

创建 AI Fiction 应用的所有核心数据表（共 15 张），含精细化增强：
  - 自动更新 updated_at 的数据库触发器
  - 关键业务字段的列注释
  - 精简索引（移除 PostgreSQL 主键自动索引的冗余声明）

Revision ID: 0001
Revises:
Create Date: 2026-05-24 19:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 所有包含 updated_at 列的表名（用于批量创建/删除触发器）
_UPDATED_AT_TABLES = [
    "user",
    "user_preference",
    "project",
    "world_setting",
    "character",
    "outline",
    "outline_node",
    "chapter",
    "chapter_version",
    "generation_task",
    "story_state_trail",
    "content_audit_log",
    "audit_log",
    "template",
]

# ── helpers ────────────────────────────────────────────────────────────
_UUID_PK = lambda: sa.Column(
    "id",
    postgresql.UUID(as_uuid=True),
    primary_key=True,
    server_default=sa.text("gen_random_uuid()"),
)
_TIMESTAMP_COL = lambda name, **kw: sa.Column(
    name,
    sa.TIMESTAMP(timezone=True),
    nullable=False,
    server_default=sa.text("now()"),
    **kw,
)
_JSONB_COL = lambda name, default="'{}'::jsonb", nullable=False, **kw: sa.Column(
    name,
    postgresql.JSONB,
    nullable=nullable,
    server_default=sa.text(default) if nullable is not False else sa.text(default),
    **kw,
)


def _create_updated_at_trigger() -> None:
    """创建公共触发器函数 + 为每张表挂载 BEFORE UPDATE 触发器"""
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    for tbl in _UPDATED_AT_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{tbl}_updated_at
                BEFORE UPDATE ON {tbl}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def _drop_updated_at_trigger() -> None:
    """卸载所有 updated_at 触发器并删除函数"""
    for tbl in _UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl};")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")


def _add_column_comments() -> None:
    """为核心业务字段添加数据库注释"""
    comments = {
        # user
        ("user", "email"): "用户邮箱（用作登录账号）",
        ("user", "password_hash"): "bcrypt / argon2 哈希后的密码",
        ("user", "oauth_provider"): "OAuth 提供商，如 google / github",
        ("user", "is_active"): "账户是否启用",
        ("user", "is_superuser"): "是否超级管理员",
        # project
        ("project", "genre"): "小说类型：xianxia / xuanhuan / urban / sci_fi / history …",
        ("project", "target_length"): "目标篇幅：short / medium / long / epic",
        ("project", "writing_style"): "风格配置 JSON：{tone, pace, perspective, …}",
        ("project", "status"): "项目状态：draft / outlining / generating / completed / archived",
        ("project", "generation_mode"): "生成模式：auto / manual / hybrid",
        # character
        ("character", "role_type"): "角色类型：protagonist / antagonist / supporting / cameo",
        ("character", "genre_specific_fields"): "按题材扩展的角色属性 JSON",
        ("character", "relationships"): "角色关系列表 JSON：[{target_id, relation_type, description}]",
        # outline
        ("outline", "is_confirmed"): "大纲是否已确认（确认后方可生成章节内容）",
        # outline_node
        ("outline_node", "chapter_number"): "章节序号",
        ("outline_node", "key_events"): "关键事件列表 JSON：[{summary, characters_involved, …}]",
        ("outline_node", "foreshadowing_items"): "本章埋下的伏笔列表 JSON",
        ("outline_node", "foreshadowing_resolved"): "本章回收的伏笔列表 JSON",
        # chapter
        ("chapter", "status"): "章节状态：planned / drafting / reviewing / completed / failed",
        ("chapter", "quality_label"): "质量标签：excellent / good / acceptable / poor",
        ("chapter", "branch_name"): "分支名称（用于故事分支功能）",
        # chapter_version
        ("chapter_version", "trigger_type"): "触发类型：ai_generation / manual_edit / retry / polish / expand",
        ("chapter_version", "is_active"): "是否为当前激活的版本",
        # generation_task
        ("generation_task", "task_type"): "任务类型：full_generation / chapter_generation / outline_generation / character_deepening",
        ("generation_task", "status"): "任务状态：pending / running / completed / failed / cancelled",
        ("generation_task", "current_stage"): "当前执行阶段名称",
        # content_audit_log
        ("content_audit_log", "audit_type"): "审核类型：quality / safety / style / consistency",
        ("content_audit_log", "audit_result"): "审核结果：pass / warn / fail",
        # audit_log
        ("audit_log", "action"): "操作动作：create / update / delete / export / generate",
        ("audit_log", "resource_type"): "资源类型：project / chapter / character / outline …",
        # template
        ("template", "genre"): "模板适用的小说类型",
        ("template", "target_length"): "模板适用的篇幅规格",
        ("template", "usage_count"): "模板被使用的次数",
    }
    for (table, column), comment in comments.items():
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{comment}';")


def upgrade() -> None:
    # ================================================================
    # 1. user（无 FK 依赖，所有表的基础）
    # ================================================================
    op.create_table(
        "user",
        _UUID_PK(),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_uid", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_user_oauth", "user", ["oauth_provider", "oauth_uid"])

    # ================================================================
    # 2. user_preference（FK → user，1:1）
    # ================================================================
    op.create_table(
        "user_preference",
        _UUID_PK(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("quality_threshold", sa.String(20), nullable=False, server_default=sa.text("'standard'")),
        sa.Column("daily_word_limit", sa.Integer, server_default=sa.text("3000")),
        sa.Column("monthly_budget_cents", sa.Integer, server_default=sa.text("500")),
        sa.Column("preferred_model", sa.String(50), nullable=True),
        sa.Column("language", sa.String(10), server_default=sa.text("'zh-CN'")),
        sa.Column("notification_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )

    # ================================================================
    # 3. project（FK → user）
    # ================================================================
    op.create_table(
        "project",
        _UUID_PK(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("target_length", sa.String(20), nullable=False),
        _JSONB_COL("writing_style"),
        sa.Column("story_brief", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("current_chapter_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("total_word_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("generation_mode", sa.String(20), nullable=True),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_project_user_id", "project", ["user_id"])
    op.create_index("idx_project_status", "project", ["status"])
    op.create_index("idx_project_user_status", "project", ["user_id", "status"])

    # ================================================================
    # 4. world_setting（FK → project，1:1）
    # ================================================================
    op.create_table(
        "world_setting",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("original_content", sa.Text, nullable=True),
        sa.Column("expanded_content", sa.Text, nullable=True),
        _JSONB_COL("structured_data"),
        sa.Column("is_expanded", sa.Boolean, nullable=False, server_default=sa.text("false")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )

    # ================================================================
    # 5. character（FK → project）
    # ================================================================
    op.create_table(
        "character",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("appearance", sa.Text, nullable=True),
        sa.Column("personality", sa.Text, nullable=True),
        sa.Column("background", sa.Text, nullable=True),
        sa.Column("role_type", sa.String(20), nullable=False, server_default=sa.text("'supporting'")),
        _JSONB_COL("genre_specific_fields"),
        sa.Column("deepened_profile", sa.Text, nullable=True),
        _JSONB_COL("relationships", default="'[]'::jsonb"),
        sa.Column("growth_arc", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default=sa.text("0")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_character_project_id", "character", ["project_id"])

    # ================================================================
    # 6. outline（FK → project，1:1）
    # ================================================================
    op.create_table(
        "outline",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )

    # ================================================================
    # 7. outline_node（FK → outline；unique(outline_id, chapter_number)）
    # ================================================================
    op.create_table(
        "outline_node",
        _UUID_PK(),
        sa.Column(
            "outline_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("outline.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chapter_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        _JSONB_COL("key_events", default="'[]'::jsonb"),
        sa.Column("emotional_arc", sa.Text, nullable=True),
        sa.Column("writing_guide", sa.Text, nullable=True),
        _JSONB_COL("foreshadowing_items", default="'[]'::jsonb"),
        _JSONB_COL("foreshadowing_resolved", default="'[]'::jsonb"),
        sa.Column("sort_order", sa.Integer, nullable=False),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
        sa.UniqueConstraint("outline_id", "chapter_number"),
    )
    op.create_index("idx_outline_node_outline_id", "outline_node", ["outline_id"])

    # ================================================================
    # 8. chapter（FK → project, outline_node, 自身）
    # ================================================================
    op.create_table(
        "chapter",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outline_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("outline_node.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chapter_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'planned'")),
        sa.Column("quality_score", sa.Integer, nullable=True),
        sa.Column("quality_label", sa.String(20), nullable=True),
        sa.Column("current_version_number", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "branch_parent_chapter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chapter.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("branch_name", sa.String(100), nullable=True),
        sa.Column("word_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
        sa.UniqueConstraint("project_id", "chapter_number", "branch_name"),
    )
    op.create_index("idx_chapter_project_id", "chapter", ["project_id"])
    op.create_index("idx_chapter_status", "chapter", ["project_id", "status"])

    # ================================================================
    # 9. chapter_version（FK → chapter；unique(chapter_id, version_number)）
    # ================================================================
    op.create_table(
        "chapter_version",
        _UUID_PK(),
        sa.Column(
            "chapter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chapter.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_summary", sa.String(200), nullable=True),
        sa.Column("word_count", sa.Integer, nullable=False),
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("modification_instruction", sa.Text, nullable=True),
        sa.Column("quality_score", sa.Integer, nullable=True),
        _JSONB_COL("quality_details"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("diff_from_previous", sa.Text, nullable=True),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
        sa.UniqueConstraint("chapter_id", "version_number"),
    )
    op.create_index("idx_version_chapter_id", "chapter_version", ["chapter_id"])

    # ================================================================
    # 10. generation_task（FK → project）
    # ================================================================
    op.create_table(
        "generation_task",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("current_stage", sa.String(30), nullable=True),
        sa.Column("progress", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_chapters", sa.Integer, server_default=sa.text("0")),
        sa.Column("completed_chapters", sa.Integer, server_default=sa.text("0")),
        _JSONB_COL("result_summary"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_stage", sa.String(30), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("max_retry", sa.Integer, server_default=sa.text("3")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_gtask_project_id", "generation_task", ["project_id"])
    op.create_index("idx_gtask_status", "generation_task", ["status"])

    # ================================================================
    # 11. task_log（FK → generation_task）
    # NOTE: TaskLog 继承 Base 而非 BaseModel，无 updated_at 列
    # ================================================================
    op.create_table(
        "task_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("log_level", sa.String(10), nullable=False, server_default=sa.text("'info'")),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        _TIMESTAMP_COL("created_at"),
    )
    op.create_index("idx_tlog_task_id", "task_log", ["task_id"])

    # ================================================================
    # 12. story_state_trail（FK → project）
    # ================================================================
    op.create_table(
        "story_state_trail",
        _UUID_PK(),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_at", sa.TIMESTAMP(timezone=True), nullable=False),
        _JSONB_COL("character_matrix"),
        _JSONB_COL("timeline", default="'[]'::jsonb"),
        _JSONB_COL("foreshadowing", default="'[]'::jsonb"),
        _JSONB_COL("items_resources"),
        _JSONB_COL("scene_states"),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_sstrail_project_id", "story_state_trail", ["project_id"])

    # ================================================================
    # 13. content_audit_log（FK → chapter_version）
    # ================================================================
    op.create_table(
        "content_audit_log",
        _UUID_PK(),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chapter_version.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("audit_type", sa.String(20), nullable=False),
        sa.Column("audit_result", sa.String(20), nullable=False),
        _JSONB_COL("flagged_sections", default="'[]'::jsonb"),
        _JSONB_COL("audit_details"),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )

    # ================================================================
    # 14. audit_log（FK → user，SET NULL）
    # ================================================================
    op.create_table(
        "audit_log",
        _UUID_PK(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        _JSONB_COL("details"),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_alog_user_id", "audit_log", ["user_id"])
    op.create_index("idx_alog_resource", "audit_log", ["resource_type", "resource_id"])

    # ================================================================
    # 15. template（FK → user；source_project_id 为逻辑引用，非 FK）
    # ================================================================
    op.create_table(
        "template",
        _UUID_PK(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("source_project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("genre", sa.String(50), nullable=False),
        sa.Column("target_length", sa.String(20), nullable=False),
        _JSONB_COL("writing_style"),
        sa.Column("story_brief", sa.Text, nullable=True),
        _JSONB_COL("world_setting"),
        _JSONB_COL("characters", default="'[]'::jsonb"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        _TIMESTAMP_COL("created_at"),
        _TIMESTAMP_COL("updated_at"),
    )
    op.create_index("idx_template_user_id", "template", ["user_id"])
    op.create_index("idx_template_genre", "template", ["genre"])

    # ── 增强 ─────────────────────────────────────────────────────────
    _create_updated_at_trigger()
    _add_column_comments()


def downgrade() -> None:
    # ── 先卸除触发器 ──────────────────────────────────────────────────
    _drop_updated_at_trigger()

    # ── 按依赖逆序删除表 ─────────────────────────────────────────────
    op.drop_index("idx_template_genre", table_name="template")
    op.drop_index("idx_template_user_id", table_name="template")
    op.drop_table("template")

    op.drop_index("idx_alog_resource", table_name="audit_log")
    op.drop_index("idx_alog_user_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_table("content_audit_log")

    op.drop_index("idx_sstrail_project_id", table_name="story_state_trail")
    op.drop_table("story_state_trail")

    op.drop_index("idx_tlog_task_id", table_name="task_log")
    op.drop_table("task_log")

    op.drop_index("idx_gtask_status", table_name="generation_task")
    op.drop_index("idx_gtask_project_id", table_name="generation_task")
    op.drop_table("generation_task")

    op.drop_index("idx_version_chapter_id", table_name="chapter_version")
    op.drop_table("chapter_version")

    op.drop_index("idx_chapter_status", table_name="chapter")
    op.drop_index("idx_chapter_project_id", table_name="chapter")
    op.drop_table("chapter")

    op.drop_index("idx_outline_node_outline_id", table_name="outline_node")
    op.drop_table("outline_node")

    op.drop_table("outline")

    op.drop_index("idx_character_project_id", table_name="character")
    op.drop_table("character")

    op.drop_table("world_setting")

    op.drop_index("idx_project_user_status", table_name="project")
    op.drop_index("idx_project_status", table_name="project")
    op.drop_index("idx_project_user_id", table_name="project")
    op.drop_table("project")

    op.drop_table("user_preference")

    op.drop_index("idx_user_oauth", table_name="user")
    op.drop_table("user")
