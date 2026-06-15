LOCAL_REVISE_MODES = {"target_sentence_fix", "target_paragraph_fix", "target_context_fix"}
FULL_CHAPTER_REPAIR_MODES = {
    "quality_light_fix",
    "quality_group_fix",
    "audit_full_rewrite",
    "repair",
    "de_ai",
    "humanize",
    "make_easy",
    "dialogue_natural",
    "punctuation_fix",
    "add_scene_texture",
    "strengthen_hook",
    "strengthen_readthrough",
}

def _split_hook_marker(content: str) -> tuple[str, str]:
    text = content or ""
    if "[HOOK]" not in text:
        return text, ""
    before, after = text.rsplit("[HOOK]", 1)
    hook_text = after.strip()
    if "[NEW_CHARACTERS]" in hook_text:
        hook_text = hook_text.split("[NEW_CHARACTERS]", 1)[0].strip()
    return before.strip(), hook_text

def _effective_original_hook(original_content: str, original_hook: str = "") -> str:
    if (original_hook or "").strip():
        return original_hook.strip()
    _, embedded_hook = _split_hook_marker(original_content)
    return embedded_hook.strip()

def _restore_missing_hook_marker(
    original_content: str,
    new_content: str,
    original_hook: str = "",
    revised_hook: str = "",
) -> tuple[str, str, bool]:
    effective_hook = (revised_hook or "").strip() or _effective_original_hook(original_content, original_hook)
    if not effective_hook or "[HOOK]" in (new_content or ""):
        return new_content, effective_hook, False
    restored_content = f"{(new_content or '').rstrip()}\n\n[HOOK] {effective_hook}".strip()
    return restored_content, effective_hook, True

def _detect_fresh_chapter_hook_loss(content: str) -> bool:
    """新写章节未带 [HOOK] 标记视为 hook 丢失回归（repair 有原 hook 可补，新写无原 hook 可补，需重试）。"""
    return "[HOOK]" not in (content or "")

def _validate_fresh_chapter(
    content: str,
    min_words: int,
    previous_content: str = "",
    expect_hook: bool = True,
) -> list[str]:
    """新写章节硬闸：返回失败原因列表（空列表表示通过）。
    - 长度：低于 min_words * 0.7 视为过短（新写无原长可比，按目标字数）
    - hook 存在性：expect_hook 时必须含 [HOOK] 标记
    - 重复上一章：复用 _previous_overlap_fragment 防止复制上一章场景
    与 repair 的 _validate_full_chapter_revision 不同：repair 有原文可比对长度比和 hook，新写没有原文，故按目标字数和标记存在性判断。
    """
    failures: list[str] = []
    text = (content or "").strip()
    if min_words and len(text) < int(min_words * 0.7):
        failures.append(
            f"新写章节正文过短：目标 {min_words} 字，实际约 {len(text)} 字，低于目标 70%。"
        )
    if expect_hook and _detect_fresh_chapter_hook_loss(text):
        failures.append("新写章节缺少章末钩子 [HOOK] 标记。")
    if previous_content:
        duplicate = _previous_overlap_fragment(previous_content, text)
        if duplicate:
            failures.append(f"新写章节疑似复制上一章正文。重复片段：{duplicate}...")
    return failures

def _revision_min_ratio(mode: str) -> float:
    if mode in {"quality_light_fix", "quality_group_fix", "de_ai", "humanize", "make_easy", "dialogue_natural", "punctuation_fix"}:
        return 0.9
    if mode in {"audit_full_rewrite", "repair", "strengthen_readthrough"}:
        return 0.78
    return 0.82

def _normalize_for_overlap(text: str) -> str:
    return "".join((text or "").split())

def _previous_overlap_fragment(previous_content: str, new_content: str, min_chars: int = 140) -> str:
    prev = _normalize_for_overlap(previous_content)
    new = _normalize_for_overlap(new_content)
    if len(prev) < min_chars or len(new) < min_chars:
        return ""
    window = max(min_chars, 180)
    step = max(40, window // 3)
    for start in range(0, max(1, len(prev) - window + 1), step):
        fragment = prev[start:start + window]
        if len(fragment) >= min_chars and fragment in new:
            return fragment[:120]
    return ""

def _validate_full_chapter_revision(original_content: str, new_content: str, original_hook: str, mode: str, previous_content: str = "") -> None:
    original_len = len((original_content or "").strip())
    new_len = len((new_content or "").strip())
    if original_len >= 1500:
        min_len = int(original_len * _revision_min_ratio(mode))
        if new_len < min_len:
            raise RuntimeError(
                f"AI 修复输出过短，本次未写入正文：原文约 {original_len} 字，修复后约 {new_len} 字，低于最低保留阈值 {min_len} 字。"
            )
    effective_original_hook = _effective_original_hook(original_content, original_hook)
    if effective_original_hook and "[HOOK]" not in (new_content or ""):
        raise RuntimeError("AI 修复丢失章末钩子，本次未写入正文。")
    duplicate = _previous_overlap_fragment(previous_content, new_content)
    if duplicate:
        raise RuntimeError(
            f"AI 修复疑似复制上一章正文，本次未写入正文。重复片段：{duplicate}..."
        )
