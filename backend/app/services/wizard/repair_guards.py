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
    if "[HOOK]" in (original_content or "") and not ("[HOOK]" in new_content or (original_hook or "").strip()):
        raise RuntimeError("AI 修复丢失章末钩子，本次未写入正文。")
    duplicate = _previous_overlap_fragment(previous_content, new_content)
    if duplicate:
        raise RuntimeError(
            f"AI 修复疑似复制上一章正文，本次未写入正文。重复片段：{duplicate}..."
        )
