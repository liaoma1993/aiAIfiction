"""
AI Fiction - 测试配置与 Fixtures

提供异步测试客户端、数据库会话、认证辅助工具等 fixtures。
使用 SQLite 内存数据库进行隔离的单元/集成测试。
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app as fastapi_app

# ============================================================
# 测试数据库 URL（SQLite 内存模式）
# ============================================================
_TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# ============================================================
# 覆盖默认设置（确保测试环境隔离）
# ============================================================
from app.config import settings

settings.SECRET_KEY = "test-secret-key-for-testing-only"
settings.DATABASE_URL = _TEST_DATABASE_URL


# ============================================================
# SQLite 兼容性处理：
#   1. PostgreSQL 特有类型映射：JSONB → JSON、TIMESTAMP(timezone=True) → DATETIME
#   2. func.gen_random_uuid() → Python uuid4()
# ============================================================

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


def _make_sqlite_compatible():
    """注册 SQLite 方言的类型编译规则，使 JSONB 在 SQLite 中可用。"""
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")  # type: ignore[arg-type]
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return compiler.visit_JSON(type_, **kw)


_make_sqlite_compatible()


def _sqlite_uuid_default(context):
    """为 SQLite 的主键生成 Python UUID 作为默认值。"""
    import uuid as _uuid
    return str(_uuid.uuid4())


_test_engine = create_async_engine(
    _TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


def _register_sqlite_functions(dbapi_connection):
    """在 SQLite 连接上注册 PostgreSQL 兼容函数。"""
    dbapi_connection.execute("PRAGMA foreign_keys=ON")
    dbapi_connection.execute("PRAGMA journal_mode=WAL")
    _gen_uuid = lambda: uuid.uuid4().hex
    try:
        dbapi_connection.create_function("gen_random_uuid", 0, _gen_uuid)
    except Exception:
        pass  # 函数已存在


@event.listens_for(_test_engine.sync_engine, "connect")
def _sqlite_on_connect(dbapi_connection, connection_record):
    """每个新连接时注册兼容函数。"""
    _register_sqlite_functions(dbapi_connection)


_test_async_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================
# 将测试引擎注入 database 模块，防止创建第二套引擎
# 这确保 app.workers.generation 等模块导入时使用测试数据库
# ============================================================

import app.database as _db_mod

_db_mod._engine = _test_engine
_db_mod._async_session_local = _test_async_session_factory

# 同时为 database 模块的引擎注册 SQLite 兼容函数
@event.listens_for(_test_engine.sync_engine, "connect")
def _db_sqlite_on_connect(dbapi_connection, connection_record):
    _register_sqlite_functions(dbapi_connection)


# ============================================================
# 预加载 workers 模块并 mock Celery 任务调用
# 避免 test_generation Mock 触发真实 Celery App 扫描
# ============================================================

from unittest.mock import MagicMock

_mock_celery_task = MagicMock()
_mock_celery_task.id = "mock-celery-task-id"

# 虽然 worker 模块会因我们的 _engine / _async_session_local 替换
# 而正常加载，这里仍为安全起见预先 mock delay() 调用
try:
    import app.workers.generation as _gen_mod  # noqa: E402

    _orig_run = _gen_mod.run_generation_pipeline
    _orig_cancel = _gen_mod.cancel_generation
    _mock_run = MagicMock()
    _mock_run.delay.return_value = _mock_celery_task
    _mock_cancel = MagicMock()
    _mock_cancel.delay.return_value = _mock_celery_task
    _gen_mod.run_generation_pipeline = _mock_run
    _gen_mod.cancel_generation = _mock_cancel
except Exception:
    _orig_run = _orig_cancel = _mock_run = _mock_cancel = None

# Mock rule compliance check Celery task
try:
    import app.workers.rule_compliance as _rc_mod  # noqa: E402

    _orig_rc_check = _rc_mod.run_rule_compliance_check
    _mock_rc_check = MagicMock()
    _mock_rc_check.delay.return_value = _mock_celery_task
    _rc_mod.run_rule_compliance_check = _mock_rc_check
except Exception:
    _orig_rc_check = _mock_rc_check = None


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="session")
def event_loop():
    """会话级事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎并建表。"""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _test_engine
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """提供独立的数据库会话（每个测试函数级）。"""
    async with _test_async_session_factory() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """提供异步 HTTP 测试客户端，注入测试数据库会话。

    覆盖 FastAPI 的 get_db 依赖，使所有 API 操作使用测试会话。
    """

    async def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ============================================================
# 用户 & 认证辅助 Fixtures
# ============================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict:
    """创建一个测试用户并返回用户信息。"""
    from app.models.user import User
    from app.models.user_preference import UserPreference
    from app.utils.security import hash_password

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"test-{user_id.hex}@example.com",
        password_hash=hash_password("TestPass123"),
        nickname="测试用户",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    preference = UserPreference(user_id=user_id)
    db_session.add(preference)
    await db_session.flush()
    return {"id": user_id, "email": f"test-{user_id.hex}@example.com", "password": "TestPass123"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """获取已认证用户的 Authorization 头。

    先注册/登录获取 token，返回带 Bearer token 的请求头字典。
    """
    from app.utils.security import create_access_token

    token = create_access_token(str(test_user["id"]))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession) -> dict:
    """创建第二个测试用户（用于测试跨用户隔离）。"""
    from app.models.user import User
    from app.models.user_preference import UserPreference
    from app.utils.security import hash_password

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"other-{user_id.hex}@example.com",
        password_hash=hash_password("OtherPass123"),
        nickname="其他用户",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    preference = UserPreference(user_id=user_id)
    db_session.add(preference)
    await db_session.flush()
    return {"id": user_id, "email": f"other-{user_id.hex}@example.com", "password": "OtherPass123"}


@pytest_asyncio.fixture
async def auth_headers_2(test_user_2: dict) -> dict:
    """第二个用户的认证头。"""
    from app.utils.security import create_access_token

    token = create_access_token(str(test_user_2["id"]))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: dict) -> dict:
    """创建一个测试项目并返回项目信息。"""
    from app.models.project import Project
    from app.models.world_setting import WorldSetting

    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        user_id=test_user["id"],
        title="测试小说项目",
        genre="xianxia",
        target_length="long",
        writing_style={"tags": ["轻松幽默"], "description": "轻松搞笑的修仙日常"},
        story_brief="一个废柴杂役弟子的逆袭故事",
        generation_mode="interactive",
    )
    db_session.add(project)

    world = WorldSetting(project_id=project_id)
    db_session.add(world)
    await db_session.flush()

    return {"id": project_id, "title": "测试小说项目"}


@pytest_asyncio.fixture
async def test_character(db_session: AsyncSession, test_project: dict) -> dict:
    """创建一个测试角色。"""
    from app.models.character import Character

    char_id = uuid.uuid4()
    char = Character(
        id=char_id,
        project_id=test_project["id"],
        name="测试主角",
        gender="male",
        age=18,
        personality="勇敢善良",
        role_type="protagonist",
        sort_order=0,
    )
    db_session.add(char)
    await db_session.flush()
    return {"id": char_id, "name": "测试主角", "project_id": str(test_project["id"])}


@pytest_asyncio.fixture
async def test_chapter(
    db_session: AsyncSession, test_project: dict
) -> dict:
    """创建一个测试章节及其初始版本。"""
    from app.models.chapter import Chapter
    from app.models.chapter_version import ChapterVersion

    chapter_id = uuid.uuid4()
    chapter = Chapter(
        id=chapter_id,
        project_id=test_project["id"],
        chapter_number=1,
        title="第一章：初入仙门",
        status="completed",
    )
    db_session.add(chapter)
    await db_session.flush()

    version = ChapterVersion(
        chapter_id=chapter_id,
        version_number=1,
        content="这是第一章的测试内容，主角来到仙门参加入门测试。",
        word_count=20,
        trigger_type="ai_generated",
        is_active=True,
    )
    db_session.add(version)
    await db_session.flush()

    return {"id": chapter_id, "project_id": str(test_project["id"]), "chapter_number": 1}


@pytest_asyncio.fixture
async def test_outline(db_session: AsyncSession, test_project: dict) -> dict:
    """创建测试大纲（project 创建时已自动创建 outline，这里直接查询返回）。"""
    from app.models.outline import Outline

    result = await db_session.execute(
        __import__("sqlalchemy").select(Outline).where(
            Outline.project_id == test_project["id"]
        )
    )
    outline = result.scalar_one_or_none()
    if outline is None:
        outline_id = uuid.uuid4()
        outline = Outline(
            id=outline_id,
            project_id=test_project["id"],
        )
        db_session.add(outline)
        await db_session.flush()
    return {"id": outline.id, "project_id": str(outline.project_id)}


@pytest_asyncio.fixture
async def test_template(
    db_session: AsyncSession, test_project: dict, test_user: dict
) -> dict:
    """创建一个测试模板。"""
    from app.models.template import Template

    template_id = uuid.uuid4()
    template = Template(
        id=template_id,
        user_id=test_user["id"],
        name="仙侠通用模板",
        description="适合仙侠题材的通用设定模板",
        genre="xianxia",
        target_length="long",
        writing_style={"tags": ["轻松幽默"], "description": "轻松搞笑"},
        story_brief="一个废柴的逆袭",
        world_setting={"description": "修仙世界"},
        characters=[
            {"name": "主角", "role_type": "protagonist"},
        ],
    )
    db_session.add(template)
    await db_session.flush()

    return {
        "id": template_id,
        "name": "仙侠通用模板",
        "user_id": str(test_user["id"]),
    }


@pytest_asyncio.fixture
async def test_foreshadowing(
    db_session: AsyncSession, test_project: dict
) -> dict:
    """创建一个测试伏笔用于 API 测试。"""
    from app.models.foreshadowing_plan import ForeshadowingPlan

    plan_id = uuid.uuid4()
    plan = ForeshadowingPlan(
        id=plan_id,
        project_id=test_project["id"],
        name="测试伏笔-神秘信件",
        description="主角收到一封无名信件",
        type="clue",
        importance="major",
        status="planned",
    )
    db_session.add(plan)
    await db_session.flush()
    return {"id": plan_id, "project_id": str(test_project["id"]), "name": plan.name}
