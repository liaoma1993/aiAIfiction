"""
AI Fiction - 生成流水线编排 (GenerationPipeline)

7 阶段小说生成流水线：
  1. 世界观扩写 (world_building)
  2. 角色深化 (character_deepening)
  3. 大纲生成 (outline_gen)
  4. 章节拆分 (chapter_split)
  5. 逐章写作 (writing)
  6. 连贯性审查 (coherence_check)
  7. 全局润色 (polish)

每个阶段自动更新任务进度、记录日志，阶段失败时记录错误并终止流水线。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Awaitable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.provider_pool import pool as _llm_pool
from app.models.chapter import Chapter
from app.models.chapter_version import ChapterVersion
from app.models.character import Character
from app.models.generation_task import GenerationTask
from app.models.outline import Outline, OutlineNode
from app.models.project import Project
from app.models.story_state_trail import StoryStateTrail
from app.models.world_setting import WorldSetting
from app.services.context_service import ContextManager
from app.services.generation_service import (
    add_log,
    complete_task,
    fail_task,
    update_progress,
)

logger = logging.getLogger(__name__)

# 阶段进度权重（微调：增加写入阶段权重，细化检查和润色阶段）
STAGE_PROGRESS_MAP = {
    "world_building": (0, 8),
    "character_deepening": (8, 18),
    "outline_gen": (18, 33),
    "chapter_split": (33, 46),
    "writing": (46, 78),
    "coherence_check": (78, 92),
    "polish": (92, 100),
}

# 写作阶段质量评估阈值（满分 100）
QUALITY_PASS_THRESHOLD = 70
# 写作阶段最大重试次数
MAX_WRITING_RETRIES = 3

# 通知回调类型
ProgressCallback = Callable[[str, int, str], Awaitable[None]] | None


class GenerationPipeline:
    """小说生成流水线编排器

    执行完整的 7 阶段 AI 生成流水线，每个阶段可独立运行、失败停止。
    通过 progress_callback 推送进度更新给 WebSocket 客户端。

    使用方式:
        pipeline = GenerationPipeline()
        result = await pipeline.execute(db, task, project)
    """

    def __init__(
        self,
        progress_callback: ProgressCallback = None,
        precision_config: Optional[dict] = None,
    ):
        """
        Args:
            progress_callback: 进度通知回调，签名 (stage: str, progress: int, message: str) -> None
            precision_config: 精细度控制配置，可选。为 None 时回退到默认行为。
        """
        self._progress_callback = progress_callback
        self._context_manager = ContextManager()
        self.precision_config = precision_config

    # =====================================================================
    #  流水线主入口
    # =====================================================================

    async def execute(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
    ) -> dict:
        """执行完整的 7 阶段生成流水线

        Args:
            db: 数据库会话
            task: 生成任务实例
            project: 所属项目

        Returns:
            {
                "status": "completed" | "failed",
                "task_id": str,
                "chapters_written": int,
                "total_word_count": int,
                "error_stage": str | None,
                "error_message": str | None,
            }
        """
        from app.services.generation_service import start_task

        # 若 constructor 未传入 precision_config，尝试从 task 读取
        if self.precision_config is None:
            if task.precision_config:
                self.precision_config = dict(task.precision_config)
            else:
                # 回退到 balanced 预设值
                self.precision_config = {
                    "preset": "balanced",
                    "world_constraint_strictness": 0.7,
                    "character_consistency_strictness": 0.7,
                    "foreshadowing_tracking_precision": 0.7,
                    "relationship_awareness": 0.7,
                    "creativity_level": 0.5,
                    "quality_threshold": 70,
                    "style_intensity": 0.5,
                }

        result_summary: dict = {
            "status": "running",
            "task_id": str(task.id),
            "chapters_written": 0,
            "total_word_count": 0,
            "error_stage": None,
            "error_message": None,
        }

        try:
            await start_task(db, task.id)
            await self._notify_progress(db, task, "world_building", 0, "流水线启动")

            # Stage 1: 世界观扩写
            world_setting = await self._stage_world_building(db, task, project)

            # Stage 2: 角色深化
            characters = await self._stage_character_deepening(db, task, project)

            # Stage 3: 大纲生成
            outline = await self._stage_outline_gen(db, task, project, world_setting, characters)

            # Stage 4: 章节拆分
            chapters = await self._stage_chapter_split(db, task, project, outline)

            # Stage 5: 逐章写作
            chapters = await self._stage_writing(db, task, project, chapters)

            # Stage 6: 连贯性审查
            issues = await self._stage_coherence_check(db, task, project, chapters)

            # Stage 7: 全局润色
            chapters = await self._stage_polish(db, task, project, chapters, issues)

            # 汇总结果
            total_words = sum(
                (await self._get_chapter_word_count(db, ch.id)) or 0
                for ch in chapters
            )
            result_summary.update({
                "status": "completed",
                "chapters_written": len(chapters),
                "total_word_count": total_words,
            })

            await self._notify_progress(db, task, "polish", 100, "生成完成")
            await complete_task(db, task.id, result_summary)
            await add_log(
                db, task.id, "polish", "info",
                f"流水线完成：共{len(chapters)}章，{total_words}字",
            )

        except Exception as exc:
            error_stage = task.current_stage or "unknown"
            error_message = str(exc)
            logger.exception(
                "Pipeline failed at stage '%s': %s", error_stage, error_message
            )
            await fail_task(db, task.id, error_stage, error_message)
            await add_log(
                db, task.id, error_stage, "error",
                error_message,
                {"error": error_message},
            )
            result_summary.update({
                "status": "failed",
                "error_stage": error_stage,
                "error_message": error_message,
            })

        return result_summary

    # =====================================================================
    #  Stage 1: 世界观扩写
    # =====================================================================

    async def _stage_world_building(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
    ) -> WorldSetting:
        """Stage 1: 调用 LLM 扩写世界观

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目

        Returns:
            更新后的 WorldSetting 实例
        """
        stage = "world_building"
        await self._notify_stage_start(db, task, stage, "正在扩写世界观设定...")

        # 获取世界观
        result = await db.execute(
            select(WorldSetting).where(WorldSetting.project_id == project.id)
        )
        world_setting = result.scalar_one_or_none()

        if world_setting is None:
            world_setting = WorldSetting(project_id=project.id)
            db.add(world_setting)

        original = world_setting.original_content or project.story_brief or project.title

        # 精细度：世界观约束严格度
        world_strictness = self.precision_config.get("world_constraint_strictness", 0.7)
        strictness_hint = ""
        if world_strictness >= 0.8:
            strictness_hint = (
                "\n\n【严格约束】请严格按照世界观规则生成，不允许任何自相矛盾。"
                "所有设定必须内部自洽，新设定必须与已有设定兼容。"
                "如发现潜在矛盾，请在输出中明确指出并给出调和方案。"
            )
        elif world_strictness >= 0.5:
            strictness_hint = "\n\n请注意保持世界观内部一致性，避免明显矛盾。"

        # 结构化编码指导
        structure_hint = (
            "\n\n请按以下结构化格式输出世界观设定：\n"
            "1. 【地理环境】\n2. 【社会结构】\n3. 【力量体系/科技水平】\n"
            "4. 【历史背景】\n5. 【文化习俗】\n6. 【特殊规则】\n\n"
            "每个类别以"# 类别名"开头，规则条款用"- "列表形式呈现，"
            "确保每条规则都是独立的约束声明，便于后续自动引用。"
        )

        # 调用 LLM 扩写
        llm = _llm_pool.get_provider_for_stage(stage)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个资深小说世界观设计师。请根据用户提供的基础设定，"
                    "进行深度扩写，构建完整的世界观体系。"
                    "请涵盖以下维度：地理环境、社会结构、力量体系/科技水平、"
                    "历史背景、文化习俗、特殊规则。"
                    "请用中文输出，内容详尽但不冗余。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"小说类型：{project.genre}\n"
                    f"基础设定：{original}\n\n"
                    "请扩写并结构化这个世界观设定。"
                    f"{strictness_hint}{structure_hint}"
                ),
            },
        ]

        response: LLMResponse = await llm.generate(
            messages, max_tokens=2000, temperature=0.7
        )

        world_setting.original_content = original
        world_setting.expanded_content = response.content
        world_setting.is_expanded = True
        await db.flush()
        await db.refresh(world_setting)

        await self._notify_stage_complete(db, task, stage, "世界观扩写完成")
        return world_setting

    # =====================================================================
    #  Stage 2: 角色深化
    # =====================================================================

    async def _stage_character_deepening(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
    ) -> list[Character]:
        """Stage 2: 逐角色深化

        对每个角色调用 LLM 进行深度化描写，包括性格动机、行为模式、
        语言特色、成长弧线等。

        精细度增强: 根据 character_consistency_strictness 调整 prompt 要求，
        strictness >= 0.8 时要求输出三个约束块（行为模式、语言风格、情感表达），
        并解析存入 Character 模型的 3 个 JSONB 字段。

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目

        Returns:
            深化后的 Character 列表
        """
        stage = "character_deepening"
        await self._notify_stage_start(db, task, stage, "正在深化角色设定...")

        # 获取所有角色（批量查询）
        result = await db.execute(
            select(Character)
            .where(Character.project_id == project.id)
            .order_by(Character.sort_order)
        )
        characters = list(result.scalars().all())

        if not characters:
            await self._notify_stage_complete(db, task, stage, "无角色需要深化")
            return []

        # 获取世界观文本
        world_result = await db.execute(
            select(WorldSetting).where(WorldSetting.project_id == project.id)
        )
        world_setting = world_result.scalar_one_or_none()
        world_text = world_setting.expanded_content or world_setting.original_content or "" if world_setting else ""

        # 精细度：角色一致性严格度
        char_strictness = self.precision_config.get("character_consistency_strictness", 0.7)

        llm = _llm_pool.get_provider_for_stage(stage)

        for i, character in enumerate(characters):
            progress = self._calc_progress(
                stage, sub_progress=i, sub_total=len(characters)
            )
            await self._notify_progress(
                db, task, stage, progress, f"深化角色: {character.name}"
            )

            profile = (
                f"姓名：{character.name}\n"
                f"性别：{character.gender or '未知'}\n"
                f"年龄：{character.age or '未知'}\n"
                f"角色定位：{character.role_type}\n"
                f"外貌：{character.appearance or '未设定'}\n"
                f"性格：{character.personality or '未设定'}\n"
                f"背景：{character.background or '未设定'}\n"
                f"备注：{character.notes or '无'}\n"
            )

            # 高严格度：要求输出结构化约束块
            constraint_requirement = ""
            if char_strictness >= 0.8:
                constraint_requirement = (
                    "\n\n请在角色档案之后，额外以 JSON 格式输出以下三个约束块（用三个代码块包裹）：\n\n"
                    "```json behavioral\n"
                    "{\n"
                    '  "under_pressure": "压力下的反应描述",\n'
                    '  "with_strangers": "对陌生人态度",\n'
                    '  "with_loved_ones": "对亲近之人态度",\n'
                    '  "decision_style": "决策风格描述",\n'
                    '  "habits": ["习惯动作1", "口头禅1"],\n'
                    '  "moral_bottom_line": "道德底线",\n'
                    '  "fears": ["恐惧1"],\n'
                    '  "motivations": ["核心动机1"]\n'
                    "}\n"
                    "```\n\n"
                    "```json linguistic\n"
                    "{\n"
                    '  "verbosity": "简洁/中等/话多",\n'
                    '  "sentence_length": "短句为主/中短句为主/中长句为主",\n'
                    '  "habitual_phrases": ["口头禅"],\n'
                    '  "tone": "语气描述",\n'
                    '  "vocabulary_level": "词汇水平描述",\n'
                    '  "signature_expressions": ["标志性表达"]\n'
                    "}\n"
                    "```\n\n"
                    "```json emotional\n"
                    "{\n"
                    '  "anger": "愤怒时的表达方式",\n'
                    '  "sadness": "悲伤时的表达方式",\n'
                    '  "joy": "喜悦时的表达方式",\n'
                    '  "love": "表达爱意的方式",\n'
                    '  "fear": "恐惧时的表达方式",\n'
                    '  "surprise": "惊讶时的表达方式"\n'
                    "}\n"
                    "```\n"
                )
            elif char_strictness >= 0.5:
                constraint_requirement = (
                    "\n\n请在角色档案中明确包含以下维度的描述："
                    "行为模式（压力下、对待他人）、语言特色、情感表达方式。"
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个小说角色设计师。请深度分析并扩展角色的性格档案。"
                        "输出包含：核心动机、行为模式、语言特色、内在冲突、"
                        "成长弧线、与世界观的关系、潜在剧情触发点。"
                        f"{'请严格确保角色特征前后一致，所有设定必须自洽。' if char_strictness >= 0.8 else ''}"
                        "请用中文输出，不要使用 markdown 格式（除JSON代码块外）。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"世界观：{world_text[:1000]}\n\n"
                        f"角色基础信息：\n{profile}\n\n"
                        "请为此角色生成深化的角色档案。"
                        f"{constraint_requirement}"
                    ),
                },
            ]

            response: LLMResponse = await llm.generate(
                messages, max_tokens=900, temperature=0.7
            )
            character.deepened_profile = response.content

            # 高严格度时解析结构化约束块并存入 Character 模型
            if char_strictness >= 0.8:
                try:
                    behavioral = self._parse_constraint_block(response.content, "behavioral")
                    linguistic = self._parse_constraint_block(response.content, "linguistic")
                    emotional = self._parse_constraint_block(response.content, "emotional")

                    if behavioral:
                        character.behavior_patterns = behavioral
                    if linguistic:
                        character.linguistic_style = linguistic
                    if emotional:
                        character.emotional_expression = emotional
                except Exception:
                    logger.exception("Failed to parse constraint blocks for character %s", character.name)

            await db.flush()

        await self._notify_stage_complete(
            db, task, stage, f"角色深化完成: {len(characters)}个角色"
        )
        return characters

    @staticmethod
    def _parse_constraint_block(text: str, block_type: str) -> dict | None:
        """从 LLM 响应中解析指定类型的 JSON 约束块

        Args:
            text: LLM 响应全文
            block_type: 约束块类型（'behavioral' | 'linguistic' | 'emotional'）

        Returns:
            解析后的 dict，解析失败返回 None
        """
        try:
            # 匹配 ```json <type>\n{...}\n``` 格式
            import re
            pattern = rf"```json\s+{block_type}\s*\n(.*?)```"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
        except Exception:
            pass
        return None

    # =====================================================================
    #  Stage 3: 大纲生成
    # =====================================================================

    async def _stage_outline_gen(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
        world_setting: WorldSetting,
        characters: list[Character],
    ) -> Outline:
        """Stage 3: 生成小说大纲

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目
            world_setting: 世界观
            characters: 角色列表

        Returns:
            生成的大纲实例
        """
        stage = "outline_gen"
        await self._notify_stage_start(db, task, stage, "正在生成大纲...")

        # 组装角色概要
        char_summaries = "\n".join(
            f"- {c.name}（{c.role_type}）："
            f"{c.deepened_profile[:300] if c.deepened_profile else c.personality or '未设定'}"
            for c in characters[:10]
        )

        world_text = world_setting.expanded_content or world_setting.original_content or ""
        story_brief = project.story_brief or project.title

        llm = _llm_pool.get_provider_for_stage(stage)

        # 根据目标篇幅确定章节数
        chapter_count = self._estimate_chapter_count(project.target_length)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个小说大纲策划专家。请根据提供的世界观、角色设定和故事梗概，"
                    "生成一个完整的章节大纲。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"目标章节数：约 {chapter_count} 章\n"
                    f"小说类型：{project.genre}\n"
                    f"故事梗概：{story_brief}\n\n"
                    f"世界观：{world_text[:2000]}\n\n"
                    f"角色概要：\n{char_summaries}\n\n"
                    "请以 JSON 格式返回大纲，格式如下：\n"
                    '{\n'
                    '  "nodes": [\n'
                    '    {\n'
                    '      "chapter_number": 1,\n'
                    '      "title": "章节标题",\n'
                    '      "summary": "本章概要（200-500字）",\n'
                    '      "key_events": ["关键事件1", "关键事件2"],\n'
                    '      "emotional_arc": "本章角色情绪变化描述",\n'
                    '      "writing_guide": "详细的写作指南（300-800字）",\n'
                    '      "foreshadowing_items": ["新埋伏笔"],\n'
                    '      "foreshadowing_resolved": ["回收伏笔"]\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
            },
        ]

        response = await llm.generate_json(
            messages, temperature=0.8, max_tokens=4000
        )

        nodes_data = response.get("nodes", [])

        # 获取或创建大纲
        outline_result = await db.execute(
            select(Outline).where(Outline.project_id == project.id)
        )
        outline = outline_result.scalar_one_or_none()

        if outline is None:
            outline = Outline(project_id=project.id)
            db.add(outline)
        else:
            # 清除旧节点
            old_nodes_result = await db.execute(
                select(OutlineNode).where(OutlineNode.outline_id == outline.id)
            )
            for old_node in old_nodes_result.scalars().all():
                await db.delete(old_node)

        await db.flush()

        # 创建大纲节点
        for i, node_data in enumerate(nodes_data):
            node = OutlineNode(
                outline_id=outline.id,
                chapter_number=node_data.get("chapter_number", i + 1),
                title=node_data.get("title"),
                summary=node_data.get("summary", ""),
                key_events=node_data.get("key_events", []),
                emotional_arc=node_data.get("emotional_arc"),
                writing_guide=node_data.get("writing_guide"),
                foreshadowing_items=node_data.get("foreshadowing_items", []),
                foreshadowing_resolved=node_data.get("foreshadowing_resolved", []),
                sort_order=node_data.get("chapter_number", i + 1),
            )
            db.add(node)

        outline.version += 1
        outline.is_confirmed = True
        await db.flush()
        await db.refresh(outline)

        task.total_chapters = len(nodes_data)
        await db.flush()

        # 精细度增强：自动生成伏笔计划
        await self._generate_foreshadowing_if_needed(
            db, project, outline
        )

        await self._notify_stage_complete(
            db, task, stage, f"大纲生成完成: {len(nodes_data)}章"
        )
        return outline

    async def _generate_foreshadowing_if_needed(
        self,
        db: AsyncSession,
        project: Project,
        outline: Outline,
    ) -> None:
        """根据大纲自动调用 ForeshadowingService 的 LLM 辅助方法生成伏笔计划

        根据 foreshadowing_tracking_precision 决定是否触发：
          - precision < 0.4：跳过伏笔自动生成
          - precision >= 0.4：调用 LLM 生成伏笔计划

        Args:
            db: 数据库会话
            project: 项目
            outline: 大纲实例
        """
        foreshadowing_precision = self.precision_config.get(
            "foreshadowing_tracking_precision", 0.7
        )

        if foreshadowing_precision < 0.4:
            logger.info("Foreshadowing precision too low (%.2f), skipping auto-generation", foreshadowing_precision)
            return

        try:
            from app.services.foreshadowing_service import generate_foreshadowing_from_outline

            nodes = sorted(outline.outline_nodes or [], key=lambda n: n.sort_order)
            plans = await generate_foreshadowing_from_outline(
                db=db,
                project_id=project.id,
                nodes=nodes,
                project_genre=project.genre or "",
                project_brief=project.story_brief or project.title or "",
            )
            if plans:
                logger.info(
                    "Auto-generated %d foreshadowing plans for project %s",
                    len(plans), project.id,
                )
        except Exception:
            logger.exception("Foreshadowing auto-generation failed (non-blocking)")

    # =====================================================================
    #  Stage 4: 章节拆分
    # =====================================================================

    async def _stage_chapter_split(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
        outline: Outline,
    ) -> list[Chapter]:
        """Stage 4: 拆分章节并生成写作指南

        为每个大纲节点创建对应的 Chapter 记录，并细化写作指南。

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目
            outline: 大纲

        Returns:
            Chapter 列表
        """
        stage = "chapter_split"
        await self._notify_stage_start(db, task, stage, "正在拆分章节...")

        # 清除旧章节（同一项目下）
        old_result = await db.execute(
            select(Chapter).where(
                Chapter.project_id == project.id,
                Chapter.branch_name == None,
            )
        )
        for old_chapter in old_result.scalars().all():
            await db.delete(old_chapter)
        await db.flush()

        # 加载大纲节点
        nodes_result = await db.execute(
            select(OutlineNode)
            .where(OutlineNode.outline_id == outline.id)
            .order_by(OutlineNode.sort_order)
        )
        nodes = list(nodes_result.scalars().all())

        chapters: list[Chapter] = []
        for node in nodes:
            chapter = Chapter(
                project_id=project.id,
                outline_node_id=node.id,
                chapter_number=node.chapter_number,
                title=node.title,
                status="planned",
            )
            db.add(chapter)
            chapters.append(chapter)

        await db.flush()
        project.current_chapter_count = len(chapters)
        await db.flush()

        await self._notify_stage_complete(
            db, task, stage, f"章节拆分完成: {len(chapters)}章"
        )
        return chapters

    # =====================================================================
    #  Stage 5: 逐章写作
    # =====================================================================

    async def _stage_writing(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
        chapters: list[Chapter],
    ) -> list[Chapter]:
        """Stage 5: 逐章写作（带质量评估和重试）

        对每章：
          1. 获取上下文（ContextManager）
          2. 调用写作 Prompt 生成正文
          3. 保存版本
          4. 质量评估
          5. 不达标则重试（最多 3 次）

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目
            chapters: 章节列表

        Returns:
            更新后的 Chapter 列表
        """
        stage = "writing"
        await self._notify_stage_start(db, task, stage, "开始逐章写作...")

        llm_writing = _llm_pool.get_provider_for_stage("writing")
        llm_eval = _llm_pool.get_provider_for_stage("quality_eval")

        for i, chapter in enumerate(chapters):
            chapter_progress = self._calc_progress(
                stage, sub_progress=i, sub_total=len(chapters)
            )
            await self._notify_progress(
                db, task, stage, chapter_progress,
                f"写作第{chapter.chapter_number}章: {chapter.title or ''}",
            )

            await self._write_single_chapter(
                db, chapter, project, llm_writing, llm_eval
            )

            task.completed_chapters = i + 1
            project.current_chapter_count = max(
                project.current_chapter_count, i + 1
            )
            await db.flush()

        await self._notify_stage_complete(
            db, task, stage, f"逐章写作完成: {len(chapters)}章"
        )
        return chapters

    async def _write_single_chapter(
        self,
        db: AsyncSession,
        chapter: Chapter,
        project: Project,
        llm_writing: BaseLLMProvider,
        llm_eval: BaseLLMProvider,
    ) -> None:
        """写作单章（含质量评估和重试）

        精细度增强:
          - 传入 precision_config 给 ContextManager 以生成约束卡和关系卡
          - 根据 quality_threshold 调整通过标准
          - 关键场景使用更高质量要求
        """
        # 精细化：根据 precision_config 调整质量阈值
        quality_threshold = self.precision_config.get("quality_threshold", QUALITY_PASS_THRESHOLD)

        # 检查是否为关键场景
        is_key_scene = await self._is_key_scene_chapter(db, chapter)
        if is_key_scene:
            # 关键场景提高质量阈值（加 10 分，上限 95）
            quality_threshold = min(quality_threshold + 10, 95)
            logger.info(
                "Chapter %d is a key scene, quality threshold raised to %d",
                chapter.chapter_number, quality_threshold,
            )

        for retry in range(MAX_WRITING_RETRIES):
            # 获取上下文（传入 precision_config 以启用约束卡和关系卡）
            ctx = await self._context_manager.get_context_for_chapter(
                db, chapter, project, self.precision_config
            )

            # 构建写作 Prompt
            content = await self._generate_chapter_content(
                llm_writing, chapter, project, ctx, retry
            )

            # 计算字数
            word_count = self._count_chinese_chars(content)

            # 保存版本
            version_number = chapter.current_version_number + 1
            version = ChapterVersion(
                chapter_id=chapter.id,
                version_number=version_number,
                content=content,
                content_summary=content[:200] if len(content) > 200 else content,
                word_count=word_count,
                trigger_type="generation",
                is_active=True,
            )
            db.add(version)
            await db.flush()

            # 质量评估
            quality = await self._evaluate_quality(
                llm_eval, content, chapter, project, ctx
            )

            version.quality_score = quality.get("score", 0)
            version.quality_details = quality
            chapter.quality_score = quality.get("score", 0)
            chapter.quality_label = quality.get("label", "standard")
            chapter.current_version_number = version_number
            chapter.word_count = word_count

            if quality.get("score", 0) >= quality_threshold:
                chapter.status = "completed"
                chapter.retry_count = retry
                await db.flush()
                return

            # 不达标，使用反馈重试
            feedback = quality.get("feedback", "请改进内容质量")
            chapter.retry_count += 1
            await db.flush()
            logger.info(
                "Chapter %d retry %d: score=%d (threshold=%d), feedback=%s",
                chapter.chapter_number, retry + 1,
                quality.get("score", 0), quality_threshold, feedback[:100],
            )

        # 达到最大重试次数，标记为需要审核
        chapter.status = "needs_review"
        chapter.retry_count = MAX_WRITING_RETRIES
        await db.flush()
        logger.warning(
            "Chapter %d reached max retries, marked as needs_review",
            chapter.chapter_number,
        )

    @staticmethod
    async def _is_key_scene_chapter(
        db: AsyncSession,
        chapter: Chapter,
    ) -> bool:
        """检查章节是否为关键场景

        Args:
            db: 数据库会话
            chapter: 章节实例

        Returns:
            True 如果关联的大纲节点标记为关键场景
        """
        if not chapter.outline_node_id:
            return False

        result = await db.execute(
            select(OutlineNode.is_key_scene).where(
                OutlineNode.id == chapter.outline_node_id
            )
        )
        is_key = result.scalar_one_or_none()
        return bool(is_key)

    async def _generate_chapter_content(
        self,
        llm: BaseLLMProvider,
        chapter: Chapter,
        project: Project,
        ctx: dict,
        retry_count: int = 0,
    ) -> str:
        """调用 LLM 生成章节正文"""
        # 组装上下文
        compressed = ctx.get("compressed", {})
        rolling = ctx.get("rolling_window", [])
        world_text = ctx.get("world_setting", "")
        outline_guide = ctx.get("outline_guide", "")

        # 精细度增强：约束卡和关系卡
        constraint_cards = ctx.get("constraint_cards", "")
        relationship_cards = ctx.get("relationship_cards", "")

        # 滚动窗口文本
        recent_text = ""
        if rolling:
            parts = []
            for rw in rolling:
                parts.append(
                    f"=== 第{rw['chapter_number']}章 {rw.get('title', '')} ===\n"
                    f"{rw.get('content', '')[-3000:]}"
                )
            recent_text = "\n\n".join(parts)

        # 检索段落
        retrieved = ctx.get("retrieved_paragraphs", [])
        retrieved_text = ""
        if retrieved:
            rp_parts = []
            for rp in retrieved[:5]:
                rp_parts.append(f"[{rp.get('source', '')}]\n{rp.get('text', '')}")
            retrieved_text = "\n\n".join(rp_parts)

        retry_hint = ""
        if retry_count > 0:
            retry_hint = (
                f"\n\n注意：这是第 {retry_count + 1} 次重试。"
                "请根据之前的质量反馈改进内容，增加文学性和细节描写。"
            )

        # 约束卡和关系卡文本块
        constraint_text = ""
        if constraint_cards:
            constraint_text = f"\n\n角色行为约束卡：\n{constraint_cards[:1600]}"

        relationship_text = ""
        if relationship_cards:
            relationship_text = f"\n\n角色关系卡：\n{relationship_cards[:1000]}"

        # 创造力水平影响 temperature
        creativity = self.precision_config.get("creativity_level", 0.5)
        temperature = 0.5 + creativity * 0.5  # 映射到 0.5-1.0

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的小说作家，擅长创作引人入胜的叙事内容。"
                    "请根据提供的世界观、角色信息、前后章节上下文和大纲指南，"
                    "创作本章节的完整内容。\n\n"
                    "写作要求：\n"
                    "- 保持风格一致性和角色性格还原\n"
                    "- 注意上下文衔接，避免剧情矛盾\n"
                    "- 适当的环境描写和人物心理刻画\n"
                    "- 对话自然流畅，符合角色设定\n"
                    "- 本章内容应是一个相对完整的叙事单元"
                    f"{'\\n- 严格遵守角色约束卡的行为模式和语言风格' if constraint_cards else ''}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"小说类型：{project.genre}\n"
                    f"写作风格：{project.writing_style}\n"
                    f"目标章节：第{chapter.chapter_number}章 {chapter.title or ''}\n\n"
                    f"世界观设定：\n{world_text[:1500] if world_text else '无'}\n\n"
                    f"故事进展摘要：\n"
                    f"{compressed.get('story_summary', '无')}\n\n"
                    f"角色当前状态：\n"
                    f"{compressed.get('character_matrix', '无')}"
                    f"{constraint_text}{relationship_text}\n\n"
                    f"本章大纲/写作指南：\n{outline_guide or '无'}\n\n"
                    f"最近章节内容：\n{recent_text[-3000:] if recent_text else '无'}\n\n"
                    f"相关段落参考：\n{retrieved_text[:1500] if retrieved_text else '无'}"
                    f"{retry_hint}\n\n"
                    "请开始创作本章内容。直接输出正文，不需要章节标题。"
                ),
            },
        ]

        response: LLMResponse = await llm.generate(
            messages, max_tokens=3000, temperature=temperature
        )
        return response.content.strip()

    async def _evaluate_quality(
        self,
        llm: BaseLLMProvider,
        content: str,
        chapter: Chapter,
        project: Project,
        ctx: dict,
    ) -> dict:
        """评估章节质量

        Returns:
            {"score": int, "label": str, "feedback": str, "dimensions": dict}
        """
        outline_guide = ctx.get("outline_guide", "")
        compressed = ctx.get("compressed", {})

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的小说内容质量评估专家。"
                    "请从多维度评估所给章节正文的质量，以 JSON 格式返回。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"小说类型：{project.genre}\n"
                    f"当前章节：第{chapter.chapter_number}章 {chapter.title or ''}\n"
                    f"本章大纲要求：{outline_guide[:500]}\n"
                    f"故事背景：{compressed.get('story_summary', '无')[:500]}\n\n"
                    f"章节正文（可能被截断）：\n{content[:3000]}\n\n"
                    "请以 JSON 格式返回评估结果：\n"
                    "{\n"
                    '  "score": 75,  // 0-100 综合评分\n'
                    '  "label": "good",  // excellent/good/standard/poor\n'
                    '  "feedback": "具体的改进建议",\n'
                    '  "dimensions": {\n'
                    '    "plot_coherence": 80,  // 剧情连贯性\n'
                    '    "character_consistency": 75,  // 角色一致性\n'
                    '    "literary_quality": 70,  // 文学性\n'
                    '    "outline_adherence": 85,  // 大纲贴合度\n'
                    '    "readability": 80  // 可读性\n'
                    "  }\n"
                    "}\n"
                ),
            },
        ]

        try:
            response = await llm.generate_json(
                messages, temperature=0.3, max_tokens=800
            )
            return {
                "score": response.get("score", 0),
                "label": response.get("label", "standard"),
                "feedback": response.get("feedback", ""),
                "dimensions": response.get("dimensions", {}),
            }
        except Exception:
            logger.exception("Quality evaluation failed for chapter %d", chapter.chapter_number)
            return {"score": 60, "label": "standard", "feedback": "评估失败，使用默认评分", "dimensions": {}}

    # =====================================================================
    #  Stage 6: 连贯性审查
    # =====================================================================

    async def _stage_coherence_check(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
        chapters: list[Chapter],
    ) -> list[dict]:
        """Stage 6: 连贯性审查

        检查所有已写章节的连贯性、一致性，发现问题清单。

        精细度增强:
          - 增加 relationship_awareness 检查维度
          - 增加 foreshadowing 一致性检查（埋设/揭晓进度追踪）
          - 将检查结果存入 StoryStateTrail

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目
            chapters: 所有章节

        Returns:
            问题列表 [{"chapter": int, "severity": str, "type": str, "description": str, "suggestion": str}]
        """
        stage = "coherence_check"
        await self._notify_stage_start(db, task, stage, "正在进行连贯性审查...")

        # 收集所有章节正文
        all_chapters_text: list[dict] = []
        for ch in chapters:
            content = await self._get_chapter_content(db, ch.id)
            if content:
                all_chapters_text.append({
                    "chapter_number": ch.chapter_number,
                    "title": ch.title or "",
                    "content": content,
                })

        if len(all_chapters_text) < 2:
            await self._notify_stage_complete(db, task, stage, "章节不足，跳过连贯性审查")
            return []

        # 构建审查文本（每章取前2000字）
        review_text = "\n".join(
            f"=== 第{c['chapter_number']}章 {c['title']} ===\n"
            f"{c['content'][:2000]}..."
            for c in all_chapters_text
        )

        # 精细度：关系感知度和伏笔追踪精度
        relationship_awareness = self.precision_config.get("relationship_awareness", 0.7)
        foreshadowing_precision = self.precision_config.get("foreshadowing_tracking_precision", 0.7)

        # 获取角色关系数据（如果 relationship_awareness >= 0.5）
        relationship_context = ""
        if relationship_awareness >= 0.5:
            relationship_context = await self._build_relationship_context(db, project.id)

        # 获取伏笔计划数据（如果 foreshadowing_precision >= 0.5）
        foreshadowing_context = ""
        if foreshadowing_precision >= 0.5:
            foreshadowing_context = await self._build_foreshadowing_context(db, project.id, chapters)

        # 增强维度描述
        extra_dimensions = ""
        extra_issue_types = ""
        if relationship_awareness >= 0.5:
            extra_dimensions += "- 角色关系一致性：角色互动是否符合设定的关系模式和阶段\n"
            extra_issue_types += "/relationship"
        if foreshadowing_precision >= 0.5:
            extra_dimensions += "- 伏笔一致性：已埋设的伏笔是否按计划发展、揭晓\n"
            extra_issue_types += "/foreshadowing"

        llm = _llm_pool.get_provider_for_stage(stage)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的小说编辑，负责审查长篇小说的连贯性和一致性。"
                    "请检查各章节之间的逻辑衔接、角色行为一致性、伏笔设置和回收、"
                    "时间线完整性和剧情节奏。"
                    f"{extra_dimensions}"
                    "以 JSON 格式返回发现的问题。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"小说类型：{project.genre}\n"
                    f"章节数：{len(all_chapters_text)}\n\n"
                    f"各章节概要：\n{review_text[:8000]}\n\n"
                    f"{relationship_context}"
                    f"{foreshadowing_context}"
                    "请以 JSON 格式返回审查结果：\n"
                    "{\n"
                    '  "overall_score": 85,  // 0-100 整体连贯性评分\n'
                    '  "issues": [\n'
                    "    {\n"
                    '      "chapter": 1,  // 问题所在章节号\n'
                    '      "severity": "high",  // high/medium/low\n'
                    f'      "type": "continuity",  // continuity/character/plot/pacing/logic{extra_issue_types}\n'
                    '      "description": "问题描述",\n'
                    '      "suggestion": "修改建议"\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                ),
            },
        ]

        try:
            response = await llm.generate_json(
                messages, temperature=0.4, max_tokens=2000
            )
            issues = response.get("issues", [])
            overall_score = response.get("overall_score", 0)
        except Exception:
            logger.exception("Coherence check failed")
            issues = []
            overall_score = 0

        # 将审查结果存入 StoryStateTrail
        await self._save_coherence_snapshot(
            db, project.id, chapters, issues, overall_score
        )

        await self._notify_stage_complete(
            db, task, stage,
            f"连贯性审查完成: 发现{len(issues)}个问题" if issues else "连贯性审查完成: 无明显问题",
        )
        return issues

    async def _save_coherence_snapshot(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapters: list[Chapter],
        issues: list[dict],
        overall_score: int,
    ) -> StoryStateTrail | None:
        """将连贯性审查结果存入 StoryStateTrail 快照

        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapters: 所有章节
            issues: 审查问题列表
            overall_score: 整体评分

        Returns:
            新建的 StoryStateTrail 实例
        """
        try:
            # 构建角色状态矩阵（从章节内容摘要中提取）
            character_matrix: dict = {}
            for ch in chapters:
                char_key = f"ch{ch.chapter_number}"
                character_matrix[char_key] = {
                    "chapter_number": ch.chapter_number,
                    "title": ch.title or "",
                    "status": ch.status,
                    "quality_score": ch.quality_score,
                }

            # 构建时间线（从章节序列中提取）
            timeline = [
                {
                    "chapter": ch.chapter_number,
                    "event": f"第{ch.chapter_number}章完成: {ch.title or ''}",
                }
                for ch in sorted(chapters, key=lambda c: c.chapter_number)
            ]

            # 构建伏笔状态
            foreshadowing_state = [
                {
                    "chapter": issue.get("chapter", 0),
                    "type": issue.get("type", ""),
                    "description": issue.get("description", ""),
                    "severity": issue.get("severity", ""),
                }
                for issue in issues
                if issue.get("type") in ("foreshadowing", "continuity")
            ]

            snapshot = StoryStateTrail(
                project_id=project_id,
                snapshot_at=datetime.now(timezone.utc),
                character_matrix=character_matrix,
                timeline=timeline,
                foreshadowing=foreshadowing_state,
                items_resources={
                    "overall_coherence_score": overall_score,
                    "total_issues": len(issues),
                    "check_dimensions": list(
                        set(issue.get("type", "") for issue in issues)
                    ),
                },
                scene_states={},
            )
            db.add(snapshot)
            await db.flush()
            logger.info(
                "Coherence snapshot saved: %d issues, score=%d",
                len(issues), overall_score,
            )
            return snapshot
        except Exception:
            logger.exception("Failed to save coherence snapshot")
            return None

    async def _build_relationship_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> str:
        """构建关系感知上下文块

        查询项目中所有角色的 relationships 字段，生成结构化的角色关系概要。

        Args:
            db: 数据库会话
            project_id: 项目 ID

        Returns:
            格式化的关系上下文文本
        """
        try:
            result = await db.execute(
                select(Character)
                .where(Character.project_id == project_id)
                .order_by(Character.sort_order)
            )
            characters = list(result.scalars().all())

            lines = ["【角色关系概览】"]
            for char in characters:
                rels = char.relationships or []
                if not rels:
                    continue
                for rel in rels:
                    if not isinstance(rel, dict):
                        continue
                    target = rel.get("target_character_name", "?")
                    rtype = rel.get("relation_type", "")
                    intensity = rel.get("intensity", 5)
                    stage = rel.get("current_stage", "")
                    lines.append(
                        f"- {char.name} ↔ {target}: {rtype}(强度{intensity})"
                        f"{' [' + stage + ']' if stage else ''}"
                    )

            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception:
            logger.exception("Failed to build relationship context")
            return ""

    async def _build_foreshadowing_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapters: list[Chapter],
    ) -> str:
        """构建伏笔一致性上下文块

        查询项目中的伏笔计划，计算埋设/揭晓进度，生成伏笔追踪报告。

        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapters: 所有章节

        Returns:
            格式化的伏笔上下文文本
        """
        try:
            from app.models.foreshadowing_plan import ForeshadowingPlan

            result = await db.execute(
                select(ForeshadowingPlan).where(
                    ForeshadowingPlan.project_id == project_id
                )
            )
            plans = list(result.scalars().all())

            if not plans:
                return ""

            max_chapter = max((ch.chapter_number for ch in chapters), default=0)

            lines = ["【伏笔追踪报告】"]
            for plan in plans:
                status = plan.status
                plant_ch = plan.plant_chapter_number
                reveal_ch = plan.reveal_chapter_number

                # 计算进度
                progress = ""
                if status == "planned" and plant_ch and plant_ch <= max_chapter:
                    progress = " ⚠ 应已埋设但状态仍为 planned"
                elif status == "planted" and reveal_ch and reveal_ch <= max_chapter:
                    progress = " ⚠ 应已揭晓但状态仍为 planted"
                elif status == "revealed":
                    progress = " ✓ 已揭晓"
                elif status == "verified":
                    progress = " ✓ 已验证"
                elif status == "orphaned":
                    progress = " ✗ 孤儿伏笔"

                lines.append(
                    f"- [{plan.importance}] {plan.name}: "
                    f"埋设 ch{plant_ch or '?'} → 揭晓 ch{reveal_ch or '?'}"
                    f" (状态: {status}){progress}"
                )

                # 限制行数（Token 控制）
                if len(lines) > 20:
                    lines.append("... (更多伏笔已省略)")
                    break

            return "\n".join(lines)
        except Exception:
            logger.exception("Failed to build foreshadowing context")
            return ""

    # =====================================================================
    #  Stage 7: 全局润色
    # =====================================================================

    async def _stage_polish(
        self,
        db: AsyncSession,
        task: GenerationTask,
        project: Project,
        chapters: list[Chapter],
        issues: list[dict],
    ) -> list[Chapter]:
        """Stage 7: 全局润色

        根据连贯性审查发现的问题，对需要修改的章节进行润色。

        Args:
            db: 数据库会话
            task: 任务实例
            project: 项目
            chapters: 所有章节
            issues: 连贯性审查发现的问题列表

        Returns:
            润色后的 Chapter 列表
        """
        stage = "polish"
        await self._notify_stage_start(db, task, stage, "正在进行全局润色...")

        if not issues:
            await self._notify_stage_complete(db, task, stage, "无问题需要润色")
            return chapters

        # 按问题严重程度排序，优先处理高严重性问题
        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_issues = sorted(
            issues, key=lambda x: severity_order.get(x.get("severity", "low"), 2)
        )

        # 按章节分组
        issues_by_chapter: dict[int, list[dict]] = {}
        for issue in sorted_issues:
            ch_num = issue.get("chapter", 0)
            if ch_num not in issues_by_chapter:
                issues_by_chapter[ch_num] = []
            issues_by_chapter[ch_num].append(issue)

        chapter_map = {ch.chapter_number: ch for ch in chapters}
        llm = _llm_pool.get_provider_for_stage(stage)

        polished_count = 0
        for i, (ch_num, ch_issues) in enumerate(issues_by_chapter.items()):
            chapter = chapter_map.get(ch_num)
            if chapter is None:
                continue

            progress = self._calc_progress(
                stage, sub_progress=i, sub_total=len(issues_by_chapter)
            )
            await self._notify_progress(
                db, task, stage, progress,
                f"润色第{ch_num}章 ({len(ch_issues)}个问题)",
            )

            content = await self._get_chapter_content(db, chapter.id)
            if not content:
                continue

            issues_text = "\n".join(
                f"- [{issue.get('severity')}] {issue.get('type')}: "
                f"{issue.get('description', '')} → {issue.get('suggestion', '')}"
                for issue in ch_issues
            )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个专业的小说润色编辑。请根据审查意见对章节内容进行润色修改，"
                        "确保修改后保持原文风格一致，只修改问题涉及的部分，"
                        "不要重写整章。直接返回修改后的完整正文。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"小说类型：{project.genre}\n"
                        f"章节：第{ch_num}章 {chapter.title or ''}\n\n"
                        f"需要修复的问题：\n{issues_text}\n\n"
                        f"原文：\n{content}\n\n"
                        "请返回润色后的完整正文。"
                    ),
                },
            ]

            try:
                response: LLMResponse = await llm.generate(
                    messages, max_tokens=3000, temperature=0.5
                )
                polished_content = response.content.strip()

                # 保存新版本
                version_number = chapter.current_version_number + 1
                version = ChapterVersion(
                    chapter_id=chapter.id,
                    version_number=version_number,
                    content=polished_content,
                    content_summary=(
                        polished_content[:200]
                        if len(polished_content) > 200
                        else polished_content
                    ),
                    word_count=self._count_chinese_chars(polished_content),
                    trigger_type="polish",
                    modification_instruction=f"全局润色：修复{len(ch_issues)}个问题",
                    is_active=True,
                )
                db.add(version)

                chapter.current_version_number = version_number
                chapter.word_count = version.word_count
                chapter.status = "completed"
                polished_count += 1

            except Exception:
                logger.exception("Polish failed for chapter %d", ch_num)

        await db.flush()

        await self._notify_stage_complete(
            db, task, stage, f"全局润色完成: 处理{polished_count}章"
        )
        return chapters

    # =====================================================================
    #  辅助方法
    # =====================================================================

    async def _notify_progress(
        self,
        db: AsyncSession,
        task: GenerationTask,
        stage: str,
        progress: int,
        message: str,
    ) -> None:
        """更新进度并推送通知"""
        await update_progress(db, task.id, stage, progress, message)
        if self._progress_callback:
            try:
                await self._progress_callback(stage, progress, message)
            except Exception:
                logger.exception("Progress callback failed")

    async def _notify_stage_start(
        self,
        db: AsyncSession,
        task: GenerationTask,
        stage: str,
        message: str,
    ) -> None:
        """通知阶段开始"""
        base_progress = STAGE_PROGRESS_MAP[stage][0]
        await self._notify_progress(db, task, stage, base_progress, message)
        await add_log(db, task.id, stage, "info", f"阶段开始: {message}")

    async def _notify_stage_complete(
        self,
        db: AsyncSession,
        task: GenerationTask,
        stage: str,
        message: str,
    ) -> None:
        """通知阶段完成"""
        end_progress = STAGE_PROGRESS_MAP[stage][1]
        await self._notify_progress(db, task, stage, end_progress, message)
        await add_log(db, task.id, stage, "info", f"阶段完成: {message}")

    @staticmethod
    def _calc_progress(
        stage: str,
        sub_progress: int,
        sub_total: int,
    ) -> int:
        """计算子任务在阶段内的进度百分比"""
        stage_range = STAGE_PROGRESS_MAP.get(stage, (0, 100))
        stage_start, stage_end = stage_range
        if sub_total <= 0:
            return stage_start
        ratio = min(sub_progress / sub_total, 1.0)
        return stage_start + int((stage_end - stage_start) * ratio)

    @staticmethod
    def _estimate_chapter_count(target_length: str) -> int:
        """根据目标篇幅估算章节数"""
        mapping = {
            "short": 10,
            "medium": 30,
            "long": 60,
        }
        return mapping.get(target_length, 20)

    @staticmethod
    def _count_chinese_chars(text: str) -> int:
        """统计中文字符数"""
        import unicodedata

        count = 0
        for c in text:
            if unicodedata.category(c).startswith("Lo"):
                count += 1
            elif ord(c) > 127:
                count += 1
            elif c.isalnum():
                count += 1
        return count

    @staticmethod
    async def _get_chapter_content(
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> str | None:
        """获取章节最新活动版本的内容"""
        result = await db.execute(
            select(ChapterVersion)
            .where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.is_active == True,
            )
            .order_by(ChapterVersion.version_number.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        return version.content if version else None

    @staticmethod
    async def _get_chapter_word_count(
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> int | None:
        """获取章节字数"""
        result = await db.execute(
            select(ChapterVersion.word_count)
            .where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.is_active == True,
            )
            .order_by(ChapterVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
