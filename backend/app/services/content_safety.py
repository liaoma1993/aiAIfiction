"""
AI Fiction - 内容安全审核服务

对 AI 生成内容进行敏感词过滤、安全检查和基础质量评估。
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.provider_pool import pool as _llm_pool
from app.models.content_audit import ContentAuditLog

logger = logging.getLogger(__name__)

# ============================================================
# 审核结果分级
# ============================================================
AUDIT_RESULT_PASSED = "passed"       # 完全通过
AUDIT_RESULT_FLAGGED = "flagged"    # 标记需人工审核
AUDIT_RESULT_BLOCKED = "blocked"    # 自动拦截

# ============================================================
# 审核类型
# ============================================================
AUDIT_TYPE_SAFETY = "safety_check"
AUDIT_TYPE_QUALITY = "quality_check"

# ============================================================
# 默认违禁词列表
# ============================================================
_DEFAULT_BANNED_WORDS = [
    # 政治类
    "反党", "反华", "颠覆国家政权", "分裂国家",
    "台独", "藏独", "疆独", "港独",
    # 暴恐类
    "恐怖主义", "恐怖袭击", "圣战", "自杀式爆炸",
    # 色情类
    "裸体", "性交", "口交", "肛交", "轮奸", "强奸",
    "淫乱", "色情网站", "成人网站", "黄片",
    # 毒品类
    "冰毒", "海洛因", "大麻", "可卡因", "摇头丸",
    "制作毒品", "贩卖毒品",
    # 赌博类
    "赌博网站", "赌场", "网赌", "时时彩", "六合彩",
    # 邪教类
    "法轮功", "全能神", "呼喊派",
    # 违禁类
    "枪支", "弹药", "炸药", "管制刀具",
]

# ============================================================
# 色情/暴力正则模式
# ============================================================
_ADULT_VIOLENCE_PATTERNS = re.compile(
    r"(性交|口交|肛交|轮奸|强奸|鸡奸|猥亵"
    r"|裸体|裸露|淫乱|淫秽|色诱|卖淫|嫖娼"
    r"|奸杀|奸污|凌辱|调教|SM|性虐"
    r"|春药|迷药|催情",
    re.IGNORECASE,
)

_SEVERE_VIOLENCE_PATTERNS = re.compile(
    r"(肢解|斩首|虐杀|酷刑|活埋|剥皮|碎尸"
    r"|屠杀|灭门|血洗|屠城)",
    re.IGNORECASE,
)

# ============================================================
# 未完成标记
# ============================================================
_INCOMPLETE_MARKERS = [
    "待续",
    "未完待续",
    "未完",
    "……",
    "...",
    "（未完）",
    "(未完)",
    "（待续）",
    "(待续)",
    "本章完",
    "下一章",
]

# ============================================================
# 政治敏感性检测 Prompt
# ============================================================
_POLITICAL_CHECK_PROMPT = """你是一个内容安全审核助手。请分析以下文本是否包含政治敏感内容。

请严格按照以下 JSON 格式返回结果：
{
  "is_sensitive": false,
  "severity": "none",
  "category": "",
  "explanation": "",
  "flagged_sections": []
}

判断标准：
- 如果文本包含对中国政府、中国共产党、中国领导人、国家政策、领土完整的攻击、侮辱或不当言论，标记为 sensitive
- 如果文本包含历史敏感事件的直接描写或评价，标记为 sensitive
- 如果文本涉及民族分裂、宗教极端主义言论，标记为 sensitive
- 普通的小说创作、架空世界观、虚构故事内容不算政治敏感

severity 取值：
- "none": 无敏感内容
- "low": 轻微擦边，可放过
- "medium": 明显敏感，需人工审核
- "high": 严重敏感，需拦截

flagged_sections 为数组，每项包含 {"text": "原文片段", "reason": "原因"}。
如果 is_sensitive 为 false，该数组为空。

请直接返回 JSON，不要包含任何其他文本。"""


@dataclass
class ContentAuditResult:
    """内容审核结果"""

    passed: bool
    """是否通过审核"""

    audit_type: str
    """审核类型 (safety_check / quality_check)"""

    flagged_sections: list[dict] = field(default_factory=list)
    """标记的问题片段列表"""

    score: int = 100
    """审核评分 0-100"""

    result_level: str = AUDIT_RESULT_PASSED
    """审核结果分级: passed / flagged / blocked"""


class ContentSafetyChecker:
    """内容安全审核器

    提供敏感词检测、LLM 政治敏感分析、色情暴力检测和基础质量检查。

    使用方式:
        checker = ContentSafetyChecker()
        result = await checker.check_content(text, audit_type="safety_check")
        if not result.passed:
            await checker.log_audit(db, version_id, ...)
    """

    def __init__(self):
        self._banned_words: list[str] = self._load_banned_words()

    # ============================================================
    # 违禁词加载
    # ============================================================

    def _load_banned_words(self) -> list[str]:
        """加载违禁词列表

        优先级：环境变量 > 默认列表。
        环境变量 CONTENT_SAFETY_BANNED_WORDS 支持逗号分隔。
        """
        env_words = os.getenv("CONTENT_SAFETY_BANNED_WORDS", "")
        if env_words:
            custom_words = [
                w.strip() for w in env_words.split(",") if w.strip()
            ]
            if custom_words:
                logger.info(
                    "Loaded %s banned words from environment variable",
                    len(custom_words),
                )
                return custom_words
        return _DEFAULT_BANNED_WORDS

    # ============================================================
    # 主入口
    # ============================================================

    async def check_content(
        self,
        text: str,
        audit_type: str = AUDIT_TYPE_SAFETY,
    ) -> ContentAuditResult:
        """对内容执行安全审核或质量检查

        Args:
            text: 待审核文本
            audit_type: 审核类型，safety_check 或 quality_check

        Returns:
            ContentAuditResult: 审核结果
        """
        if audit_type == AUDIT_TYPE_QUALITY:
            return await self._do_quality_check(text)
        else:
            return await self._do_safety_check(text)

    # ============================================================
    # 安全检查
    # ============================================================

    async def check_safety(self, text: str) -> list[dict]:
        """敏感词和安全内容检测

        依次执行三重检测：
        1. 违禁词列表匹配
        2. LLM 政治敏感分析 (GPT-4o-mini, temperature=0)
        3. 色情/暴力正则匹配

        Args:
            text: 待检测文本

        Returns:
            list[dict]: 标记的问题片段列表，每项包含
                {"text": str, "reason": str, "severity": str, "category": str}
        """
        flagged: list[dict] = []

        # --- 1. 违禁词匹配 ---
        for word in self._banned_words:
            if word in text:
                # 提取包含该词的前后文
                idx = text.find(word)
                start = max(0, idx - 20)
                end = min(len(text), idx + len(word) + 20)
                context = text[start:end]
                flagged.append({
                    "text": context.strip(),
                    "reason": f"包含违禁词: {word}",
                    "severity": "high",
                    "category": "banned_word",
                })
                logger.warning("Banned word '%s' found in content", word)

        # --- 2. LLM 政治敏感检测 ---
        try:
            llm_flagged = await self._check_political_sensitivity(text)
            flagged.extend(llm_flagged)
        except Exception as e:
            logger.warning(
                "LLM political sensitivity check failed: %s", e
            )

        # --- 3. 色情/暴力正则匹配 ---
        adult_matches = _ADULT_VIOLENCE_PATTERNS.findall(text)
        if adult_matches:
            for match in set(adult_matches):
                idx = text.find(match)
                start = max(0, idx - 10)
                end = min(len(text), idx + len(match) + 10)
                context = text[start:end]
                flagged.append({
                    "text": context.strip(),
                    "reason": f"疑似色情/不当内容: {match}",
                    "severity": "medium",
                    "category": "adult_content",
                })
            logger.warning(
                "Adult/violence keywords found: %s", adult_matches
            )

        severe_matches = _SEVERE_VIOLENCE_PATTERNS.findall(text)
        if severe_matches:
            for match in set(severe_matches):
                idx = text.find(match)
                start = max(0, idx - 10)
                end = min(len(text), idx + len(match) + 10)
                context = text[start:end]
                flagged.append({
                    "text": context.strip(),
                    "reason": f"疑似严重暴力内容: {match}",
                    "severity": "high",
                    "category": "severe_violence",
                })
            logger.warning(
                "Severe violence keywords found: %s", severe_matches
            )

        return flagged

    async def _check_political_sensitivity(self, text: str) -> list[dict]:
        """通过 LLM 检测政治敏感内容

        使用 GPT-4o-mini (temperature=0) 进行快速判断。

        Args:
            text: 待检测文本

        Returns:
            list[dict]: LLM 标记的问题片段
        """
        try:
            provider = _llm_pool.get_provider("openai_mini")
        except (ValueError, KeyError):
            logger.warning(
                "openai_mini provider not available for political check"
            )
            return []

        # 如果文本很长，只取前 2000 字进行分析
        analysis_text = text[:2000] if len(text) > 2000 else text

        messages = [
            {"role": "system", "content": _POLITICAL_CHECK_PROMPT},
            {
                "role": "user",
                "content": f"请分析以下文本：\n\n{analysis_text}",
            },
        ]

        try:
            response = await provider.generate(
                messages=messages,
                temperature=0,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            result = self._parse_json_response(response.content)

            if not result.get("is_sensitive", False):
                return []

            severity = result.get("severity", "medium")
            sections = result.get("flagged_sections", [])
            category = result.get("category", "political_sensitivity")

            flagged: list[dict] = []
            for section in sections:
                flagged.append({
                    "text": section.get("text", ""),
                    "reason": section.get("reason", "政治敏感内容"),
                    "severity": severity,
                    "category": category,
                })

            if flagged:
                logger.info(
                    "LLM flagged %d political sensitivity sections (severity=%s)",
                    len(flagged),
                    severity,
                )

            return flagged
        except Exception as e:
            logger.error("LLM political check failed: %s", e)
            return []

    @staticmethod
    def _parse_json_response(content: str) -> dict:
        """解析 LLM 返回的 JSON 响应"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and start < end:
                return json.loads(content[start : end + 1])
            raise

    # ============================================================
    # 质量检查
    # ============================================================

    async def check_quality(self, text: str) -> dict:
        """基础质量检查

        Args:
            text: 待检查文本

        Returns:
            dict: 质量检查结果
                {
                    "passed": bool,
                    "word_count": int,
                    "min_word_count": int,
                    "has_incomplete_marker": bool,
                    "incomplete_markers_found": list[str],
                    "issues": list[str],
                }
        """
        from app.utils.text_utils import count_words

        issues: list[str] = []
        word_count = count_words(text)

        # 字数检查（2000 字为最低标准）
        min_word_count = 2000
        if word_count < min_word_count:
            issues.append(
                f"字数不足: {word_count}字 < {min_word_count}字最低标准"
            )

        # 未完成标记检查
        incomplete_markers_found: list[str] = []
        for marker in _INCOMPLETE_MARKERS:
            if marker in text:
                incomplete_markers_found.append(marker)

        if incomplete_markers_found:
            issues.append(
                f"包含未完成标记: {', '.join(incomplete_markers_found)}"
            )

        return {
            "passed": len(issues) == 0,
            "word_count": word_count,
            "min_word_count": min_word_count,
            "has_incomplete_marker": len(incomplete_markers_found) > 0,
            "incomplete_markers_found": incomplete_markers_found,
            "issues": issues,
        }

    # ============================================================
    # 内部审核逻辑
    # ============================================================

    async def _do_safety_check(self, text: str) -> ContentAuditResult:
        """执行完整安全检查并生成审核结果"""
        flagged = await self.check_safety(text)

        if not flagged:
            return ContentAuditResult(
                passed=True,
                audit_type=AUDIT_TYPE_SAFETY,
                flagged_sections=[],
                score=100,
                result_level=AUDIT_RESULT_PASSED,
            )

        # 计算评分
        high_count = sum(
            1 for f in flagged if f.get("severity") == "high"
        )
        medium_count = sum(
            1 for f in flagged if f.get("severity") == "medium"
        )
        low_count = sum(
            1 for f in flagged if f.get("severity") == "low"
        )

        score = 100 - (high_count * 30 + medium_count * 15 + low_count * 5)
        score = max(0, score)

        # 分级
        if high_count > 0:
            result_level = AUDIT_RESULT_BLOCKED
        elif medium_count > 0:
            result_level = AUDIT_RESULT_FLAGGED
        else:
            result_level = AUDIT_RESULT_FLAGGED

        return ContentAuditResult(
            passed=False,
            audit_type=AUDIT_TYPE_SAFETY,
            flagged_sections=flagged,
            score=score,
            result_level=result_level,
        )

    async def _do_quality_check(self, text: str) -> ContentAuditResult:
        """执行完整质量检查并生成审核结果"""
        quality = await self.check_quality(text)

        if quality["passed"]:
            return ContentAuditResult(
                passed=True,
                audit_type=AUDIT_TYPE_QUALITY,
                flagged_sections=[],
                score=100,
                result_level=AUDIT_RESULT_PASSED,
            )

        flagged_sections = []
        for issue in quality["issues"]:
            flagged_sections.append({
                "text": issue,
                "reason": issue,
                "severity": "low",
                "category": "quality_issue",
            })

        score = 50
        if quality["word_count"] < 2000:
            score = max(0, score - 40)
        if quality["has_incomplete_marker"]:
            score = max(0, score - 30)

        return ContentAuditResult(
            passed=False,
            audit_type=AUDIT_TYPE_QUALITY,
            flagged_sections=flagged_sections,
            score=score,
            result_level=AUDIT_RESULT_FLAGGED,
        )

    # ============================================================
    # 审核日志记录
    # ============================================================

    async def log_audit(
        self,
        db: AsyncSession,
        version_id: uuid.UUID,
        audit_type: str,
        result: str,
        flagged_sections: list[dict],
    ) -> ContentAuditLog:
        """记录审核日志到 ContentAuditLog 表

        Args:
            db: 数据库会话
            version_id: 章节版本 ID
            audit_type: 审核类型
            result: 审核结果 (passed / flagged / blocked)
            flagged_sections: 标记的问题片段

        Returns:
            ContentAuditLog: 创建的审核日志记录
        """
        audit_log = ContentAuditLog(
            version_id=version_id,
            audit_type=audit_type,
            audit_result=result,
            flagged_sections=flagged_sections,
            audit_details={
                "section_count": len(flagged_sections),
                "severity_counts": await self._count_severities(flagged_sections),
            },
        )

        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)

        logger.info(
            "Audit log created: type=%s, result=%s, flagged=%d sections",
            audit_type,
            result,
            len(flagged_sections),
        )

        return audit_log

    @staticmethod
    async def _count_severities(flagged_sections: list[dict]) -> dict:
        """统计各严重级别数量"""
        counts = {"high": 0, "medium": 0, "low": 0}
        for section in flagged_sections:
            sev = section.get("severity", "low")
            if sev in counts:
                counts[sev] += 1
        return counts


# ============================================================
# 便捷工厂函数
# ============================================================

#: 全局单例
_default_checker: Optional[ContentSafetyChecker] = None


def get_safety_checker() -> ContentSafetyChecker:
    """获取全局 ContentSafetyChecker 单例"""
    global _default_checker
    if _default_checker is None:
        _default_checker = ContentSafetyChecker()
    return _default_checker
