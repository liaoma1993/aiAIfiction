import re

def _score_arc_quality(arcs: list[dict]) -> dict:
    issues: list[dict] = []
    warnings: list[dict] = []

    def meaningful_handoff(text: str) -> bool:
        text = str(text or "").strip()
        if len(text) < 18:
            return False
        vague = ("承接上一弧线", "接住上一弧线", "上一弧线终点状态", "继续推进", "后续压力", "具体交接物")
        return not any(item in text for item in vague)

    for idx, arc in enumerate(arcs or []):
        if not isinstance(arc, dict):
            continue
        required = [
            ("opening_state", "缺少弧线开局状态"),
            ("ending_state", "缺少弧线终点状态"),
            ("handoff_to_next", "缺少交给下一弧线/下一卷的具体钩子"),
            ("continuity_chain", "缺少内部因果链"),
            ("irreplaceable_value", "缺少不可替代价值"),
        ]
        if idx > 0:
            required.append(("handoff_from_previous", "缺少从上一弧线接来的具体交接物"))
        for key, message in required:
            if not arc.get(key):
                issues.append({"arc_index": idx, "name": arc.get("name", ""), "issue": message, "field": key, "critical": key in {"handoff_from_previous", "handoff_to_next", "arc_steps"}})
        steps = arc.get("arc_steps") or []
        if not isinstance(steps, list) or len(steps) < 3:
            issues.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "arc_steps 少于3个，弧线容易像摘要", "field": "arc_steps", "critical": True})
        try:
            chapter_count = int(arc.get("chapter_count") or 0)
        except (TypeError, ValueError):
            chapter_count = 0
        if chapter_count > 24:
            issues.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "chapter_count 超过24，单条弧线可能吞并了多个同级事件链", "field": "chapter_count", "critical": True})
        elif chapter_count > 18 and not _arc_is_important_for_chapter_budget(arc):
            warnings.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "普通弧线章数偏高，建议检查是否应拆成多条同级弧线", "field": "chapter_count", "critical": False})
        description = str(arc.get("description") or "")
        coarse_tokens = ("随后", "接着", "同时", "与此同时", "最终", "一年内", "两个月", "多次", "逐步")
        coarse_hits = sum(description.count(token) for token in coarse_tokens)
        if coarse_hits >= 5:
            warnings.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "弧线描述出现过多阶段连接词，可能是阶段大包而非单一事件链", "field": "description", "critical": False})
        main_change_like = sum(1 for token in ("下村", "走访", "立项", "试种", "合作社", "验收", "举报", "调查", "提拔", "晋升", "调任") if token in description)
        if main_change_like >= 4:
            warnings.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "弧线同时覆盖多个任务节点，颗粒度可能过粗", "field": "description", "critical": False})
        if idx > 0:
            prev = arcs[idx - 1] if idx - 1 < len(arcs) and isinstance(arcs[idx - 1], dict) else {}
            prev_handoff = prev.get("handoff_to_next") or prev.get("payoff_for_next") or prev.get("ending_state") or ""
            current_handoff = arc.get("handoff_from_previous") or arc.get("dependence_on_previous") or ""
            current_context = "\n".join([
                str(current_handoff or ""),
                str(arc.get("opening_state") or ""),
                str(arc.get("continuity_chain") or ""),
            ])
            has_overlap = any(token in current_context for token in re.split(r"[，。；、\s]+", str(prev_handoff)) if len(token) >= 2)
            if prev_handoff and current_handoff and not has_overlap and not meaningful_handoff(current_handoff):
                warnings.append({"arc_index": idx, "name": arc.get("name", ""), "issue": "当前弧线接收物和上一弧线交出物语义可能不一致", "field": "handoff_from_previous", "critical": False})
    score = max(0, 100 - len(issues) * 10 - len(warnings) * 4)
    return {
        "score": score,
        "passed": score >= 75 and not any(i.get("critical") for i in issues),
        "issues": issues[:20],
        "warnings": warnings[:20],
        "issue_count": len(issues),
        "warning_count": len(warnings),
    }

def _arc_quality_gate(arc_quality: dict, arc_index: int) -> dict:
    issues = [i for i in arc_quality.get("issues", []) if i.get("arc_index") == arc_index]
    warnings = [i for i in arc_quality.get("warnings", []) if i.get("arc_index") == arc_index]
    score = max(0, 100 - len(issues) * 20 - len(warnings) * 8)
    return {
        "score": score,
        "passed": score >= 75 and not any(i.get("critical") for i in issues),
        "related_issues": issues,
        "related_warnings": warnings,
    }

def _chapter_blueprint_gate(node_data: dict, idx: int, arc_index: int, previous_arc_ending: str = "") -> dict:
    issues: list[str] = []
    if not node_data.get("connects_from"):
        issues.append("缺少 connects_from，上承状态不明确")
    if not node_data.get("connects_to"):
        issues.append("缺少 connects_to，章末交接不明确")
    if not node_data.get("key_events"):
        issues.append("缺少 key_events，章节可能没有可见事件")
    if not node_data.get("arc_step_refs"):
        issues.append("缺少 arc_step_refs，未标明承载哪段弧线台阶")
    if not node_data.get("state_delta"):
        issues.append("缺少 state_delta，状态增量不明确")
    if idx == 0 and arc_index > 0 and previous_arc_ending and not node_data.get("connects_from"):
        issues.append("跨弧线第一章没有显式接住上一弧线")
    entry_checks = node_data.get("entry_gate_checks") or {}
    if isinstance(entry_checks, dict) and entry_checks.get("passed") is False:
        issues.append("角色/组织入场硬闸未通过")
    return {
        "passed": not issues,
        "score": max(0, 100 - len(issues) * 15),
        "issues": issues,
    }

def _arc_is_short_bridge(arc: dict) -> bool:
    text = " ".join(
        str(arc.get(key) or "")
        for key in ("arc_type", "narrative_function", "closure_level", "name", "description")
    )
    return any(token in text for token in ("余波过渡", "节奏缓冲", "桥接", "短插曲", "小插曲"))

def _arc_is_important_for_chapter_budget(arc: dict) -> bool:
    text = " ".join(
        str(arc.get(key) or "")
        for key in ("arc_type", "narrative_function", "name", "description", "irreplaceable_value")
    )
    important_tokens = (
        "主线目标变化",
        "主线推进",
        "高潮爆发",
        "反派压力",
        "身份风险",
        "信息揭露",
        "组织接触",
        "卷核心危机",
        "阶段质变",
        "重大认可",
        "破格提拔",
        "调查清白",
        "举报",
        "晋升",
    )
    return any(token in text for token in important_tokens)

def _arc_chapter_range_guidance(arc: dict, expansion_scale: str) -> str:
    raw_base = int(arc.get("chapter_count") or 0)
    is_short_bridge = _arc_is_short_bridge(arc)
    is_important = _arc_is_important_for_chapter_budget(arc) and not is_short_bridge
    if is_short_bridge:
        base = min(raw_base or 4, 6)
    elif is_important:
        base = min(raw_base or 14, 18)
    else:
        base = min(raw_base or 8, 12)

    if expansion_scale == "compact":
        if is_short_bridge:
            low, high = max(2, round(base * 0.65)), max(4, round(base * 0.9))
        elif is_important:
            low, high = max(8, round(base * 0.7)), min(18, max(12, round(base * 1.0)))
        else:
            low, high = max(4, round(base * 0.7)), min(12, max(6, round(base * 1.0)))
    elif expansion_scale == "long":
        if is_important:
            low, high = max(12, round(base * 1.0)), min(24, max(16, round(base * 1.35)))
        elif is_short_bridge:
            low, high = max(3, round(base * 1.0)), min(8, max(5, round(base * 1.35)))
        else:
            low, high = max(6, round(base * 1.0)), min(16, max(10, round(base * 1.5)))
    elif expansion_scale == "detailed":
        if is_important:
            low, high = max(14, round(base * 1.0)), min(24, max(18, round(base * 1.5)))
        elif is_short_bridge:
            low, high = max(4, round(base * 1.1)), min(8, max(6, round(base * 1.5)))
        else:
            low, high = max(8, round(base * 1.1)), min(18, max(12, round(base * 1.7)))
    else:
        if is_important:
            low, high = max(10, round(base * 0.85)), min(20, max(14, round(base * 1.2)))
        elif is_short_bridge:
            low, high = max(2, round(base * 0.8)), min(6, max(4, round(base * 1.2)))
        else:
            low, high = max(6, round(base * 0.85)), min(14, max(8, round(base * 1.2)))
    if high < low:
        high = low + 2
    if is_important:
        reason = "本弧线承担重要事件功能，但单条弧线仍应控制边界；超过24章通常说明应拆成多条同级弧线。"
    elif is_short_bridge:
        reason = "本弧线属于过渡/余波/桥接，应短而清楚，保留承接和余波即可。"
    else:
        reason = "本弧线按普通同级事件链处理，卷轴厚度由多条弧线共同承担。"
    return f"建议 {low}-{high} 章；{reason}这是内部范围，不要向用户询问具体章数。若弧线复杂度明显超过上限，优先回到卷轴层面拆成多条同级弧线，不要把相邻任务硬塞进本弧线。"

def _normalize_narrative_arc_payload(arcs: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for idx, raw_arc in enumerate(arcs or []):
        if not isinstance(raw_arc, dict):
            continue
        arc = dict(raw_arc)
        arc.setdefault("handoff_from_previous", arc.get("dependence_on_previous") or ("卷开局状态" if idx == 0 else "承接上一弧线终点状态"))
        arc.setdefault("handoff_to_next", arc.get("payoff_for_next") or "本弧线结尾留下的具体压力")
        arc.setdefault("continuity_chain", "")
        arc.setdefault("arc_type", "主线目标变化")
        arc.setdefault("main_change_object", arc.get("arc_type") or "本弧线主要变化对象")
        arc.setdefault("core_change", arc.get("protagonist_change") or arc.get("ending_state") or "本弧线造成的核心变化")
        arc.setdefault("closure_level", "半闭合")
        arc.setdefault("must_remain_open", [])
        arc.setdefault("bridge_chapter_plan", {"needed": idx > 0, "must_process": []})
        arc.setdefault("protagonist_continuity_state", {})
        arc.setdefault("character_lifecycle_updates", [])
        arc.setdefault("faction_lifecycle_updates", [])
        arc.setdefault("arc_review_targets", [])
        arc.setdefault("blueprint_repair_targets", [])
        arc.setdefault("compatibility_notes", "旧小说内容不自动重写；仅在用户重新生成/重拆时使用本弧线结构。")
        try:
            current_count = int(arc.get("chapter_count") or 0)
        except (TypeError, ValueError):
            current_count = 0
        if _arc_is_short_bridge(arc):
            if current_count <= 0:
                arc["chapter_count"] = 4
        elif _arc_is_important_for_chapter_budget(arc):
            if current_count <= 0:
                arc["chapter_count"] = 14
            elif current_count > 24:
                arc["chapter_count"] = 24
                targets = arc.get("arc_review_targets")
                if not isinstance(targets, list):
                    targets = []
                targets.append("当前弧线章数超过24，需检查是否吞并相邻任务；必要时拆成多条同级弧线")
                arc["arc_review_targets"] = targets
        elif current_count <= 0:
            arc["chapter_count"] = 8
        elif current_count > 18:
            arc["chapter_count"] = 18
            targets = arc.get("arc_review_targets")
            if not isinstance(targets, list):
                targets = []
            targets.append("普通弧线章数偏高，需检查颗粒度是否过粗")
            arc["arc_review_targets"] = targets
        steps = arc.get("arc_steps")
        if not isinstance(steps, list) or not steps:
            milestones = arc.get("key_milestones") or []
            fallback_steps = []
            for step_idx, item in enumerate(milestones[:5], start=1):
                label = item if isinstance(item, str) else (item.get("name") or item.get("stage") or f"关键节点{step_idx}") if isinstance(item, dict) else f"关键节点{step_idx}"
                fallback_steps.append({
                    "step_name": str(label)[:40],
                    "starting_state": arc.get("opening_state", ""),
                    "trigger_event": str(label),
                    "visible_action": "由章节展开阶段补足具体行动",
                    "friction": "由章节展开阶段补足具体阻力",
                    "state_change": "由章节展开阶段补足状态变化",
                    "consequence": arc.get("ending_state", ""),
                    "carry_forward": arc.get("handoff_to_next") or arc.get("payoff_for_next") or "",
                })
            arc["arc_steps"] = fallback_steps
        arc["bridge_check"] = {
            "requires_previous_handoff": idx > 0,
            "has_handoff_from_previous": bool(arc.get("handoff_from_previous") or arc.get("dependence_on_previous")),
            "has_handoff_to_next": bool(arc.get("handoff_to_next") or arc.get("payoff_for_next")),
            "has_arc_steps": bool(arc.get("arc_steps")),
        }
        arc.setdefault("character_introduction_plan", [])
        arc.setdefault("faction_introduction_plan", [])
        normalized.append(arc)
    for idx, arc in enumerate(normalized):
        if idx > 0:
            prev = normalized[idx - 1]
            arc["previous_handoff_hint"] = prev.get("handoff_to_next") or prev.get("payoff_for_next") or prev.get("ending_state", "")
    return normalized

def _build_arc_continuity_index(arcs: list[dict]) -> list[dict]:
    index: list[dict] = []
    for idx, arc in enumerate(arcs or []):
        if not isinstance(arc, dict):
            continue
        index.append({
            "arc_index": idx,
            "name": arc.get("name", ""),
            "arc_type": arc.get("arc_type", ""),
            "closure_level": arc.get("closure_level", ""),
            "must_remain_open": arc.get("must_remain_open") or [],
            "handoff_from_previous": arc.get("handoff_from_previous") or arc.get("dependence_on_previous") or "",
            "handoff_to_next": arc.get("handoff_to_next") or arc.get("payoff_for_next") or "",
            "opening_state": arc.get("opening_state", ""),
            "ending_state": arc.get("ending_state", ""),
            "arc_step_count": len(arc.get("arc_steps") or []) if isinstance(arc.get("arc_steps"), list) else 0,
            "previous_handoff_hint": arc.get("previous_handoff_hint", ""),
            "character_introduction_plan": arc.get("character_introduction_plan") or [],
            "faction_introduction_plan": arc.get("faction_introduction_plan") or [],
            "bridge_chapter_plan": arc.get("bridge_chapter_plan") or {},
            "protagonist_continuity_state": arc.get("protagonist_continuity_state") or {},
            "character_lifecycle_updates": arc.get("character_lifecycle_updates") or [],
            "faction_lifecycle_updates": arc.get("faction_lifecycle_updates") or [],
            "arc_review_targets": arc.get("arc_review_targets") or [],
            "blueprint_repair_targets": arc.get("blueprint_repair_targets") or [],
        })
    return index

def _build_arc_bridge_checks(arcs: list[dict]) -> list[dict]:
    checks: list[dict] = []
    for idx, arc in enumerate(arcs or []):
        if not isinstance(arc, dict):
            continue
        checks.append({
            "arc_index": idx,
            "name": arc.get("name", ""),
            "requires_previous_handoff": idx > 0,
            "has_handoff_from_previous": bool(arc.get("handoff_from_previous") or arc.get("dependence_on_previous")),
            "has_handoff_to_next": bool(arc.get("handoff_to_next") or arc.get("payoff_for_next")),
            "has_arc_steps": bool(arc.get("arc_steps")),
            "closure_level": arc.get("closure_level", ""),
            "has_entry_slope": bool(arc.get("character_introduction_plan") or arc.get("faction_introduction_plan")),
            "needs_bridge_chapter": bool((arc.get("bridge_chapter_plan") or {}).get("needed")),
            "needs_repair": (idx > 0 and not bool(arc.get("handoff_from_previous") or arc.get("dependence_on_previous"))) or not bool(arc.get("arc_steps")),
        })
    return checks
