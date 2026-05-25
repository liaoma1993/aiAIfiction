"""
AI Fiction - 精细化增强模型单元测试

测试内容：
1. Character 新增约束字段 (behavior_patterns, linguistic_style, emotional_expression)
2. OutlineNode 新增关键场景字段 (is_key_scene, scene_template)
3. GenerationTask 新增精细度配置字段 (precision_config)
4. ForeshadowingPlan 模型完整生命周期
5. RuleComplianceReport 模型违规追踪
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.character import Character
from app.models.outline import Outline, OutlineNode
from app.models.generation_task import GenerationTask
from app.models.foreshadowing_plan import ForeshadowingPlan
from app.models.rule_compliance import RuleComplianceReport


# ============================================================
# Character 约束字段测试
# ============================================================


class TestCharacterConstraints:
    """Character 模型新增 behavior_patterns, linguistic_style, emotional_expression 字段测试"""

    async def test_default_values_are_none(self, db_session: AsyncSession, test_project: dict):
        """新建角色时三个约束字段默认值为 None"""
        char = Character(
            project_id=test_project["id"],
            name="测试角色",
            role_type="protagonist",
        )
        db_session.add(char)
        await db_session.flush()

        assert char.behavior_patterns is None
        assert char.linguistic_style is None
        assert char.emotional_expression is None

    async def test_set_behavior_patterns(self, db_session: AsyncSession, test_project: dict):
        """设置完整的行为模式 JSONB 数据"""
        char = Character(
            project_id=test_project["id"],
            name="林墨",
            role_type="protagonist",
            behavior_patterns={
                "under_pressure": "用冷笑掩饰紧张，语速加快",
                "with_strangers": "礼貌但保持距离，观察多于表达",
                "with_loved_ones": "少言但行动力强，通过行为而非语言表达关心",
                "with_authority": "表面服从，暗中观察评估",
                "with_rivals": "冷静分析，不轻易表露情绪",
                "moral_bottom_line": "绝不伤害无辜",
                "decision_style": "理性分析后迅速决断，但容易忽略他人感受",
                "habits": ["摸下巴思考", "紧张时手指敲桌子"],
                "fears": ["失去重要的人", "无法保护所爱"],
                "motivations": ["成为最强的修仙者", "为师傅报仇"],
            },
        )
        db_session.add(char)
        await db_session.flush()

        # 通过重新查询验证 JSONB 往返
        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.behavior_patterns is not None
        assert loaded.behavior_patterns["under_pressure"] == "用冷笑掩饰紧张，语速加快"
        assert loaded.behavior_patterns["moral_bottom_line"] == "绝不伤害无辜"
        assert len(loaded.behavior_patterns["habits"]) == 2
        assert "摸下巴思考" in loaded.behavior_patterns["habits"]

    async def test_set_linguistic_style(self, db_session: AsyncSession, test_project: dict):
        """设置语言风格约束 JSONB 数据"""
        char = Character(
            project_id=test_project["id"],
            name="苏晴",
            role_type="protagonist",
            linguistic_style={
                "verbosity": "中等",
                "sentence_length": "中短句为主，偶尔长句抒情",
                "habitual_phrases": ["话说回来", "这事儿不简单"],
                "tone": "沉稳冷静，偶尔带黑色幽默",
                "vocabulary_level": "中等偏上，偶尔用典故",
                "dialect_or_accent": None,
                "signature_expressions": ["呵，有意思", "那就各凭本事吧"],
            },
        )
        db_session.add(char)
        await db_session.flush()

        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.linguistic_style["verbosity"] == "中等"
        assert "话说回来" in loaded.linguistic_style["habitual_phrases"]
        assert loaded.linguistic_style["dialect_or_accent"] is None
        assert len(loaded.linguistic_style["signature_expressions"]) == 2

    async def test_set_emotional_expression(self, db_session: AsyncSession, test_project: dict):
        """设置情感表达方式 JSONB 数据"""
        char = Character(
            project_id=test_project["id"],
            name="云澈",
            role_type="protagonist",
            emotional_expression={
                "anger": "冷静的愤怒，语气冰冷却更危险",
                "sadness": "独自沉默，拒绝安慰",
                "joy": "嘴角微微上扬，已是极大外露",
                "love": "从不直接说爱，但事事把她放在第一位",
                "fear": "瞳孔微微收缩，但不会退缩",
                "surprise": "眉毛微挑，仅此而已",
                "guilt": "避开目光，陷入长时间沉默",
            },
        )
        db_session.add(char)
        await db_session.flush()

        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.emotional_expression["anger"] == "冷静的愤怒，语气冰冷却更危险"
        assert loaded.emotional_expression["love"] == "从不直接说爱，但事事把她放在第一位"
        assert len(loaded.emotional_expression) == 7

    async def test_set_all_three_constraints(self, db_session: AsyncSession, test_project: dict):
        """同时设置三个约束字段"""
        char = Character(
            project_id=test_project["id"],
            name="完整角色",
            role_type="antagonist",
            behavior_patterns={"under_pressure": "暴怒，失去理智"},
            linguistic_style={"verbosity": "话多", "tone": "傲慢"},
            emotional_expression={"anger": "直接发怒，毫不掩饰"},
        )
        db_session.add(char)
        await db_session.flush()

        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.behavior_patterns is not None
        assert loaded.linguistic_style is not None
        assert loaded.emotional_expression is not None
        assert loaded.behavior_patterns["under_pressure"] == "暴怒，失去理智"
        assert loaded.linguistic_style["verbosity"] == "话多"
        assert loaded.emotional_expression["anger"] == "直接发怒，毫不掩饰"

    async def test_clear_constraints(self, db_session: AsyncSession, test_project: dict):
        """设置约束后再清空为 None"""
        char = Character(
            project_id=test_project["id"],
            name="将要清空",
            role_type="supporting",
            behavior_patterns={"test": "data"},
            linguistic_style={"test": "data"},
            emotional_expression={"test": "data"},
        )
        db_session.add(char)
        await db_session.flush()

        # 清空
        char.behavior_patterns = None
        char.linguistic_style = None
        char.emotional_expression = None
        await db_session.flush()

        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.behavior_patterns is None
        assert loaded.linguistic_style is None
        assert loaded.emotional_expression is None

    async def test_constraints_with_deeply_nested_data(self, db_session: AsyncSession, test_project: dict):
        """约束字段保存深层嵌套的 JSON 结构"""
        nested_data = {
            "under_pressure": {
                "physical": "握紧拳头",
                "verbal": "语气变冷",
                "thoughts": ["不能输", "必须找到出口"],
            },
            "triggers": [
                {"type": "betrayal", "severity": 9},
                {"type": "loss", "severity": 10},
            ],
        }
        char = Character(
            project_id=test_project["id"],
            name="嵌套角色",
            role_type="protagonist",
            behavior_patterns=nested_data,
        )
        db_session.add(char)
        await db_session.flush()

        result = await db_session.execute(
            select(Character).where(Character.id == char.id)
        )
        loaded = result.scalar_one()
        assert loaded.behavior_patterns["under_pressure"]["physical"] == "握紧拳头"
        assert loaded.behavior_patterns["triggers"][0]["type"] == "betrayal"


# ============================================================
# OutlineNode 关键场景字段测试
# ============================================================


class TestOutlineNodeKeyScene:
    """OutlineNode 模型新增 is_key_scene 和 scene_template 字段测试"""

    async def test_default_is_key_scene_is_false(self, db_session: AsyncSession, test_project: dict):
        """新建大纲节点时 is_key_scene 默认值为 False"""
        outline = Outline(project_id=test_project["id"])
        db_session.add(outline)
        await db_session.flush()

        node = OutlineNode(
            outline_id=outline.id,
            chapter_number=1,
            title="普通章节",
            summary="普通内容",
            sort_order=0,
        )
        db_session.add(node)
        await db_session.flush()

        assert node.is_key_scene is False
        assert node.scene_template is None

    async def test_mark_as_key_scene(self, db_session: AsyncSession, test_project: dict):
        """标记大纲节点为关键场景"""
        outline = Outline(project_id=test_project["id"])
        db_session.add(outline)
        await db_session.flush()

        node = OutlineNode(
            outline_id=outline.id,
            chapter_number=5,
            title="最终决战",
            summary="主角与最终BOSS的决战",
            is_key_scene=True,
            sort_order=4,
        )
        db_session.add(node)
        await db_session.flush()

        result = await db_session.execute(
            select(OutlineNode).where(OutlineNode.id == node.id)
        )
        loaded = result.scalar_one()
        assert loaded.is_key_scene is True

    async def test_set_full_scene_template(self, db_session: AsyncSession, test_project: dict):
        """设置完整的场景模板 JSONB 数据"""
        outline = Outline(project_id=test_project["id"])
        db_session.add(outline)
        await db_session.flush()

        node = OutlineNode(
            outline_id=outline.id,
            chapter_number=10,
            title="感情告白",
            summary="男女主角终于互相表白",
            is_key_scene=True,
            scene_template={
                "scene_type": "confession",
                "pacing": {"opening": "tender", "middle": "intense", "ending": "cathartic"},
                "character_spotlight": [
                    {"character_id": str(uuid.uuid4()), "weight": 0.5, "highlight_moment": "女主含泪告白"},
                    {"character_id": str(uuid.uuid4()), "weight": 0.5, "highlight_moment": "男主震惊回应"},
                ],
                "emotional_tone": "甜蜜与心酸交织，多年暗恋终得回应",
                "sensory_focus": ["视觉：夜晚的星空", "听觉：心跳声"],
                "expected_word_count": 5000,
                "quality_bar": "excellent",
                "special_requirements": ["需要内心独白", "至少3段对话交替"],
            },
            sort_order=9,
        )
        db_session.add(node)
        await db_session.flush()

        result = await db_session.execute(
            select(OutlineNode).where(OutlineNode.id == node.id)
        )
        loaded = result.scalar_one()
        assert loaded.is_key_scene is True
        assert loaded.scene_template["scene_type"] == "confession"
        assert loaded.scene_template["pacing"]["ending"] == "cathartic"
        assert len(loaded.scene_template["character_spotlight"]) == 2
        assert loaded.scene_template["quality_bar"] == "excellent"

    async def test_scene_template_various_types(self, db_session: AsyncSession, test_project: dict):
        """测试各种场景类型模板"""
        outline = Outline(project_id=test_project["id"])
        db_session.add(outline)
        await db_session.flush()

        scene_types = ["battle", "revelation", "turning_point", "climax", "intro", "resolution", "other"]
        for i, stype in enumerate(scene_types):
            node = OutlineNode(
                outline_id=outline.id,
                chapter_number=i + 1,
                title=f"{stype}场景",
                summary=f"场景描述 {stype}",
                is_key_scene=(stype in ("battle", "climax")),
                scene_template={"scene_type": stype, "quality_bar": "excellent" if stype == "climax" else "good"},
                sort_order=i,
            )
            db_session.add(node)
            await db_session.flush()

            result = await db_session.execute(
                select(OutlineNode).where(OutlineNode.id == node.id)
            )
            loaded = result.scalar_one()
            assert loaded.scene_template["scene_type"] == stype

    async def test_unmark_key_scene(self, db_session: AsyncSession, test_project: dict):
        """取消关键场景标记"""
        outline = Outline(project_id=test_project["id"])
        db_session.add(outline)
        await db_session.flush()

        node = OutlineNode(
            outline_id=outline.id,
            chapter_number=3,
            title="关键场景",
            summary="概述",
            is_key_scene=True,
            scene_template={"scene_type": "battle"},
            sort_order=2,
        )
        db_session.add(node)
        await db_session.flush()

        node.is_key_scene = False
        node.scene_template = None
        await db_session.flush()

        result = await db_session.execute(
            select(OutlineNode).where(OutlineNode.id == node.id)
        )
        loaded = result.scalar_one()
        assert loaded.is_key_scene is False
        assert loaded.scene_template is None


# ============================================================
# GenerationTask 精细度配置字段测试
# ============================================================


class TestGenerationTaskPrecisionConfig:
    """GenerationTask 模型 precision_config 字段测试"""

    async def test_default_precision_config_is_none(self, db_session: AsyncSession, test_project: dict):
        """新建生成任务时 precision_config 默认值为 None"""
        task = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            progress=0,
        )
        db_session.add(task)
        await db_session.flush()

        assert task.precision_config is None

    async def test_set_fast_preset(self, db_session: AsyncSession, test_project: dict):
        """设置 fast 预设精度的配置"""
        task = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            precision_config={
                "preset": "fast",
                "world_constraint_strictness": 0.3,
                "character_consistency_strictness": 0.3,
                "foreshadowing_tracking_precision": 0.3,
                "relationship_awareness": 0.3,
                "creativity_level": 0.8,
                "quality_threshold": 50,
                "style_intensity": 0.3,
            },
        )
        db_session.add(task)
        await db_session.flush()

        result = await db_session.execute(
            select(GenerationTask).where(GenerationTask.id == task.id)
        )
        loaded = result.scalar_one()
        assert loaded.precision_config["preset"] == "fast"
        assert loaded.precision_config["quality_threshold"] == 50
        assert loaded.precision_config["creativity_level"] == 0.8

    async def test_set_balanced_preset(self, db_session: AsyncSession, test_project: dict):
        """设置 balanced 预设精度的配置"""
        task = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            precision_config={
                "preset": "balanced",
                "world_constraint_strictness": 0.7,
                "character_consistency_strictness": 0.7,
                "foreshadowing_tracking_precision": 0.7,
                "relationship_awareness": 0.7,
                "creativity_level": 0.5,
                "quality_threshold": 70,
                "style_intensity": 0.5,
            },
        )
        db_session.add(task)
        await db_session.flush()

        result = await db_session.execute(
            select(GenerationTask).where(GenerationTask.id == task.id)
        )
        loaded = result.scalar_one()
        assert loaded.precision_config["preset"] == "balanced"
        assert loaded.precision_config["quality_threshold"] == 70

    async def test_set_precision_preset(self, db_session: AsyncSession, test_project: dict):
        """设置 precision 预设（最高精细度）的配置"""
        task = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            precision_config={
                "preset": "precision",
                "world_constraint_strictness": 0.95,
                "character_consistency_strictness": 0.95,
                "foreshadowing_tracking_precision": 0.95,
                "relationship_awareness": 0.95,
                "creativity_level": 0.2,
                "quality_threshold": 85,
                "style_intensity": 0.8,
            },
        )
        db_session.add(task)
        await db_session.flush()

        result = await db_session.execute(
            select(GenerationTask).where(GenerationTask.id == task.id)
        )
        loaded = result.scalar_one()
        assert loaded.precision_config["preset"] == "precision"
        assert loaded.precision_config["quality_threshold"] == 85
        assert loaded.precision_config["creativity_level"] == 0.2

    async def test_custom_precision_values(self, db_session: AsyncSession, test_project: dict):
        """自定义精度的配置（非预设）值"""
        task = GenerationTask(
            project_id=test_project["id"],
            task_type="chapter_only",
            status="pending",
            precision_config={
                "preset": "custom",
                "world_constraint_strictness": 0.5,
                "character_consistency_strictness": 0.9,
                "foreshadowing_tracking_precision": 0.8,
                "relationship_awareness": 0.6,
                "creativity_level": 0.4,
                "quality_threshold": 75,
                "style_intensity": 0.6,
            },
        )
        db_session.add(task)
        await db_session.flush()

        result = await db_session.execute(
            select(GenerationTask).where(GenerationTask.id == task.id)
        )
        loaded = result.scalar_one()
        assert loaded.precision_config["world_constraint_strictness"] == 0.5
        assert loaded.precision_config["character_consistency_strictness"] == 0.9

    async def test_precision_config_boundary_values(self, db_session: AsyncSession, test_project: dict):
        """精度控制参数的边界值测试"""
        # 最小值 (0.0)
        task_min = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            precision_config={
                "preset": "minimum",
                "world_constraint_strictness": 0.0,
                "character_consistency_strictness": 0.0,
                "foreshadowing_tracking_precision": 0.0,
                "relationship_awareness": 0.0,
                "creativity_level": 0.0,
                "quality_threshold": 0,
                "style_intensity": 0.0,
            },
        )
        db_session.add(task_min)
        await db_session.flush()
        assert task_min.precision_config["quality_threshold"] == 0

        # 最大值 (1.0 / 100)
        task_max = GenerationTask(
            project_id=test_project["id"],
            task_type="full_generation",
            status="pending",
            precision_config={
                "preset": "maximum",
                "world_constraint_strictness": 1.0,
                "character_consistency_strictness": 1.0,
                "foreshadowing_tracking_precision": 1.0,
                "relationship_awareness": 1.0,
                "creativity_level": 1.0,
                "quality_threshold": 100,
                "style_intensity": 1.0,
            },
        )
        db_session.add(task_max)
        await db_session.flush()
        assert task_max.precision_config["quality_threshold"] == 100


# ============================================================
# ForeshadowingPlan 模型测试
# ============================================================


class TestForeshadowingPlanModel:
    """ForeshadowingPlan 模型完整生命周期测试"""

    async def test_create_minimal_foreshadowing(self, db_session: AsyncSession, test_project: dict):
        """最简创建——仅名称和项目"""
        plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="神秘信件",
        )
        db_session.add(plan)
        await db_session.flush()

        assert plan.id is not None
        assert isinstance(plan.id, uuid.UUID)
        assert plan.type == "clue"
        assert plan.importance == "major"
        assert plan.status == "planned"
        assert plan.is_verified is False

    async def test_create_with_all_fields(self, db_session: AsyncSession, test_project: dict):
        """包含所有可选字段的完整创建"""
        plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="主角的真实身份",
            description="主角其实是仙帝转世，在第30章揭晓",
            type="identity",
            importance="critical",
            status="planned",
            plant_chapter_number=3,
            plant_detail="通过梦中的伏笔暗示主角的特殊能力",
            reveal_chapter_number=30,
            reveal_type="dramatic",
            reveal_detail="在天劫中恢复记忆，仙帝法相浮现",
            notes="这是全书最大的伏笔，揭晓时需增强戏剧性",
        )
        db_session.add(plan)
        await db_session.flush()

        assert plan.type == "identity"
        assert plan.importance == "critical"
        assert plan.plant_chapter_number == 3
        assert plan.reveal_chapter_number == 30
        assert plan.reveal_type == "dramatic"

    async def test_type_enum_values(self, db_session: AsyncSession, test_project: dict):
        """type 字段的各种枚举值测试"""
        types = ["clue", "identity", "prop", "event", "relationship"]
        for i, t in enumerate(types):
            plan = ForeshadowingPlan(
                project_id=test_project["id"],
                name=f"伏笔类型{t}",
                type=t,
            )
            db_session.add(plan)
            await db_session.flush()

            result = await db_session.execute(
                select(ForeshadowingPlan).where(ForeshadowingPlan.id == plan.id)
            )
            loaded = result.scalar_one()
            assert loaded.type == t

    async def test_importance_enum_values(self, db_session: AsyncSession, test_project: dict):
        """importance 字段的各种枚举值测试"""
        importances = ["critical", "major", "minor"]
        for i, imp in enumerate(importances):
            plan = ForeshadowingPlan(
                project_id=test_project["id"],
                name=f"重要度{imp}",
                importance=imp,
            )
            db_session.add(plan)
            await db_session.flush()
            assert plan.importance == imp

    async def test_status_enum_values(self, db_session: AsyncSession, test_project: dict):
        """status 字段的各种状态值测试（模拟生命周期）"""
        statuses = ["planned", "planted", "developing", "revealed", "verified", "orphaned"]
        for i, status in enumerate(statuses):
            plan = ForeshadowingPlan(
                project_id=test_project["id"],
                name=f"状态{status}",
                status=status,
            )
            db_session.add(plan)
            await db_session.flush()

            result = await db_session.execute(
                select(ForeshadowingPlan).where(ForeshadowingPlan.id == plan.id)
            )
            loaded = result.scalar_one()
            assert loaded.status == status

    async def test_parent_child_chain(self, db_session: AsyncSession, test_project: dict):
        """父-子伏笔链式关联"""
        parent_plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="主线大伏笔",
            type="event",
        )
        db_session.add(parent_plan)
        await db_session.flush()

        child_plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="子伏笔1",
            type="clue",
            parent_foreshadowing_id=parent_plan.id,
        )
        db_session.add(child_plan)
        await db_session.flush()

        assert child_plan.parent_foreshadowing_id == parent_plan.id

    async def test_status_lifecycle_transition(self, db_session: AsyncSession, test_project: dict):
        """伏笔状态从 planned → planted → developing → revealed → verified 完整过渡"""
        plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="生命周期测试",
        )
        db_session.add(plan)
        await db_session.flush()

        # planned → planted
        plan.status = "planted"
        await db_session.flush()
        assert plan.status == "planted"

        # planted → developing
        plan.status = "developing"
        await db_session.flush()
        assert plan.status == "developing"

        # developing → revealed
        plan.status = "revealed"
        await db_session.flush()
        assert plan.status == "revealed"

        # revealed → verified
        plan.status = "verified"
        plan.is_verified = True
        plan.verified_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert plan.status == "verified"
        assert plan.is_verified is True
        assert plan.verified_at is not None

    async def test_chapter_linkage(self, db_session: AsyncSession, test_project: dict, test_chapter: dict):
        """伏笔关联实际章节"""
        plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="章节关联伏笔",
            status="planted",
            actual_plant_chapter_id=test_chapter["id"],
            actual_plant_content="在第1章的对话中暗藏了伏笔信息",
        )
        db_session.add(plan)
        await db_session.flush()

        assert plan.actual_plant_chapter_id == test_chapter["id"]
        assert plan.actual_plant_content == "在第1章的对话中暗藏了伏笔信息"

    async def test_orphan_status(self, db_session: AsyncSession, test_project: dict):
        """废弃状态的伏笔"""
        plan = ForeshadowingPlan(
            project_id=test_project["id"],
            name="废弃的伏笔",
            status="orphaned",
            notes="由于大纲改版，此伏笔不再使用",
        )
        db_session.add(plan)
        await db_session.flush()
        assert plan.status == "orphaned"
        assert plan.notes == "由于大纲改版，此伏笔不再使用"


# ============================================================
# RuleComplianceReport 模型测试
# ============================================================


class TestRuleComplianceReportModel:
    """RuleComplianceReport 模型违规追踪测试"""

    async def test_create_clean_report(self, db_session: AsyncSession, test_project: dict):
        """创建干净的合规报告（无违规）"""
        report = RuleComplianceReport(
            project_id=test_project["id"],
            violations=[],
            violation_count=0,
            is_clean=True,
        )
        db_session.add(report)
        await db_session.flush()

        assert report.violation_count == 0
        assert report.is_clean is True
        assert report.chapter_id is None  # 项目级汇总

    async def test_create_report_with_violations(self, db_session: AsyncSession, test_project: dict, test_chapter: dict):
        """创建有违规项的合规报告"""
        report = RuleComplianceReport(
            project_id=test_project["id"],
            chapter_id=test_chapter["id"],
            violations=[
                {
                    "rule_id": "rule_001",
                    "description": "角色使用了暗系魔法但未描述生命力消耗",
                    "position": "第3段",
                    "severity": "major",
                },
                {
                    "rule_id": "rule_002",
                    "description": "修仙界灵气复苏时间线与设定矛盾",
                    "position": "第5段",
                    "severity": "critical",
                },
            ],
            violation_count=2,
            is_clean=False,
        )
        db_session.add(report)
        await db_session.flush()

        assert report.violation_count == 2
        assert report.is_clean is False
        assert report.chapter_id == test_chapter["id"]
        assert len(report.violations) == 2
        assert report.violations[0]["severity"] == "major"
        assert report.violations[1]["severity"] == "critical"

    async def test_default_values(self, db_session: AsyncSession, test_project: dict):
        """默认值验证"""
        report = RuleComplianceReport(
            project_id=test_project["id"],
        )
        db_session.add(report)
        await db_session.flush()

        assert report.violations == []  # 空列表默认值
        assert report.violation_count == 0
        assert report.is_clean is True
        assert report.chapter_id is None
        assert report.checked_at is not None

    async def test_project_level_summary(self, db_session: AsyncSession, test_project: dict):
        """项目级汇总报告（chapter_id=None）"""
        report = RuleComplianceReport(
            project_id=test_project["id"],
            chapter_id=None,
            violations=[
                {"rule_id": "rule_003", "description": "跨章统计：魔法规则违反3次", "severity": "major"},
            ],
            violation_count=1,
            is_clean=False,
        )
        db_session.add(report)
        await db_session.flush()

        assert report.chapter_id is None
        assert report.violation_count == 1

    async def test_multiple_severity_violations(self, db_session: AsyncSession, test_project: dict):
        """多种严重等级违规混合"""
        report = RuleComplianceReport(
            project_id=test_project["id"],
            violations=[
                {"rule_id": "r1", "description": "批评", "severity": "minor"},
                {"rule_id": "r2", "description": "严重警告", "severity": "major"},
                {"rule_id": "r3", "description": "致命错误", "severity": "critical"},
                {"rule_id": "r4", "description": "小问题", "severity": "minor"},
            ],
            violation_count=4,
            is_clean=False,
        )
        db_session.add(report)
        await db_session.flush()

        severities = [v["severity"] for v in report.violations]
        assert "critical" in severities
        assert "major" in severities
        assert "minor" in severities
        assert report.violation_count == 4
