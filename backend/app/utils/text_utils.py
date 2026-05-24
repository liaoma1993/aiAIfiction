"""
AI Fiction - 文本工具函数

提供中文字数统计、文本截断、摘要提取、文本清理等通用工具。
"""

import re
import unicodedata

# 中文字符 Unicode 范围（CJK 统一表意文字 + CJK 扩展 A）
_CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# 英文单词匹配模式
_ENGLISH_WORD_PATTERN = re.compile(r"[a-zA-Z]+")

# 不可见字符正则（移除控制字符，保留空格和换行）
_INVISIBLE_CHAR_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202f\u2060-\u2064\ufeff]"
)


def count_chinese_chars(text: str) -> int:
    """统计中文字数

    使用正则匹配 CJK 统一表意文字范围和 CJK 扩展 A 范围。

    Args:
        text: 输入文本

    Returns:
        int: 中文字符数量
    """
    if not text:
        return 0
    return len(_CHINESE_CHAR_PATTERN.findall(text))


def count_words(text: str) -> int:
    """统计总字数（中文 + 英文单词）

    中文字符每个计 1 字，英文单词每个计 1 词，返回总和。

    Args:
        text: 输入文本

    Returns:
        int: 总字数
    """
    if not text:
        return 0
    chinese_count = count_chinese_chars(text)
    english_count = len(_ENGLISH_WORD_PATTERN.findall(text))
    return chinese_count + english_count


def truncate_text(text: str, max_chars: int) -> str:
    """截断文本至指定字数

    Args:
        text: 输入文本
        max_chars: 最大字数限制

    Returns:
        str: 截断后的文本；若未超出限制则返回原文
    """
    if not text or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def extract_summary(text: str, max_chars: int = 100) -> str:
    """提取文本前 N 字的摘要

    取文本开头 max_chars 个字符作为摘要，若原文较短则返回全文。

    Args:
        text: 输入文本
        max_chars: 摘要最大字数，默认 100

    Returns:
        str: 摘要文本
    """
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[:max_chars]


def sanitize_text(text: str) -> str:
    """清理文本中的不可见字符

    移除控制字符、零宽字符、BOM 等不可见字符，保留空格和换行。

    Args:
        text: 输入文本

    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    # 移除不可见字符
    cleaned = _INVISIBLE_CHAR_PATTERN.sub("", text)
    # 规范化 Unicode（统一全角/半角等价字符）
    cleaned = unicodedata.normalize("NFKC", cleaned)
    return cleaned
