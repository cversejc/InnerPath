"""Traceable calendar generation with frozen skills and independent calibration."""
from copy import deepcopy
from datetime import datetime
from app.core.time import utc_now_naive, utc_now_iso
import json
from math import isfinite
import re

from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.service import _ensure_published_builtin_version, create_skill_run
from app.domains.skills.runtime import execute_skill, SkillExecutionError
from app.domains.skills.bindings import specification_digest
from app.domains.skills.examples import retrieve_skill_examples
from .skill_definitions import default_calendar_skill_specifications
from .temporal import calculate_temporal_facts
from .generation import validate_generated_calendar
from .context import calendar_model_context
from .practices import (
    plan_practice_schedule,
    project_scheduled_actions_for_authoring,
    validate_practice_entry,
    validate_practice_schedule,
)


async def ensure_calendar_skills(db):
    return [await _ensure_published_builtin_version(db, skill_key=spec["identity"]["skill_key"],
            category=category, specification=spec) for category, spec in default_calendar_skill_specifications()]


async def freeze_calendar_skills(db):
    return {v.skill_key: {"id": v.id, "version": v.version,
                         "sha256": specification_digest(v.specification_json)} for v in await ensure_calendar_skills(db)}


def select_tone(dimensions, weights, *, degraded=False):
    if set(dimensions) != set(weights) or any(not isinstance(w, (int, float)) or isinstance(w, bool)
            or not isfinite(w) or w < 0 for w in weights.values()) or abs(sum(weights.values()) - 1) > 0.001:
        raise ValueError("calendar_tone_weights_invalid")
    for dimension in dimensions.values():
        score = dimension.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not isfinite(score) or not -2 <= score <= 2 or not dimension.get("reason"):
            raise ValueError("calendar_analysis_dimension_invalid")
    score = sum(dimensions[key]["score"] * weight for key, weight in weights.items())
    if degraded:
        return "yellow", score
    return ("green" if score >= 0.7 else "blue" if score >= 0 else "yellow" if score >= -0.8 else "red"), round(score, 3)


def require_dates(rows, dates):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("calendar_stage_dates_invalid")
    actual = [row.get("entry_date") for row in rows]
    if len(actual) != len(dates) or set(actual) != set(dates):
        raise ValueError("calendar_stage_dates_invalid")


def validate_windows(windows, facts):
    periods = {w["period"] for w in facts["windows"]}
    if not isinstance(windows, list) or not 2 <= len(windows) <= 3:
        raise ValueError("calendar_windows_invalid")
    seen = set()
    for window in windows:
        if not isinstance(window, dict) or window.get("period") not in periods or window["period"] in seen or not window.get("label") or not window.get("suggestion"):
            raise ValueError("calendar_windows_invalid")
        seen.add(window["period"])


def validate_daily(row, analysis, facts, *, practice_rhythm=None, available_minutes_per_day=30,
                   scheduled_refs=None, require_action_refs=True):
    if "tone" in row and row["tone"] != analysis["tone"]:
        raise ValueError("calendar_tone_mismatch")
    if "day_pillar" in row and row["day_pillar"] != facts["day_pillar"]:
        raise ValueError("calendar_pillar_mismatch")
    if not isinstance(row.get("summary"), str) or not 30 <= len(row["summary"].strip()) <= 60:
        summary_length = len(row.get("summary", "").strip()) if isinstance(row.get("summary"), str) else 0
        raise ValueError(f"calendar_summary_length_invalid:{row.get('entry_date')}:{summary_length}")
    if not isinstance(row.get("keyword"), str) or not 2 <= len(row["keyword"].split("、")) <= 4:
        raise ValueError("calendar_keywords_invalid")
    max_suitable = min(5, max(3, 2 + len(scheduled_refs or [])))
    if (not isinstance(row.get("suitable"), list) or not 2 <= len(row["suitable"]) <= max_suitable
            or any(not isinstance(s, str) or not s.strip() for s in row["suitable"])):
        detail = {"entry_date": row.get("entry_date"),
                  "suitable_count": len(row["suitable"]) if isinstance(row.get("suitable"), list) else None,
                  "expected_range": [2, max_suitable]}
        raise ValueError("calendar_directions_invalid:" + json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
    if not row.get("energy_awareness") or not row.get("tone_explanation"):
        raise ValueError("calendar_awareness_required")
    validate_windows(row.get("windows"), facts)
    if {w["period"] for w in row["windows"]} != {w["period"] for w in analysis["windows"]}:
        raise ValueError("calendar_windows_mismatch")
    if "action_refs" not in row and not require_action_refs:
        row["action_refs"] = list(scheduled_refs or [])
    validate_practice_entry(row, practice_rhythm or {}, available_minutes_per_day, scheduled_refs)


def validate_unique_daily_awareness(rows, previous_rows=()):
    seen = {}
    duplicates = []
    for row in previous_rows:
        text = row.get("energy_awareness")
        if isinstance(text, str) and text.strip():
            seen[" ".join(text.split()).casefold()] = row.get("entry_date")
    for row in rows:
        text = row.get("energy_awareness")
        if not isinstance(text, str) or not text.strip():
            continue
        normalized = " ".join(text.split()).casefold()
        if normalized in seen:
            duplicates.append({"entry_date": row.get("entry_date"), "duplicate_of": seen[normalized]})
        else:
            seen[normalized] = row.get("entry_date")
    if duplicates:
        raise ValueError("calendar_energy_awareness_repeated:" + json.dumps(duplicates, ensure_ascii=False))


def _compact_action_fragment(action, limit):
    """Select a short, complete clause from an existing action for a summary."""
    if limit < 2:
        return ""
    clauses = [part.strip() for part in re.split(r"[，。；：！？]", action) if part.strip()]
    for clause in clauses:
        if len(clause) <= limit - 1:
            return clause
    fragment = action.strip()[: max(1, limit - 1)].rstrip("，。；：！？")
    return fragment


def complete_short_summaries(output):
    """Complete short summaries with a clause copied from the day's action."""
    changes = []
    for row in output.get("entries", []):
        if not isinstance(row, dict):
            continue
        raw_summary = row.get("summary")
        before = raw_summary.strip() if isinstance(raw_summary, str) else ""
        actions = row.get("suitable")
        if not before:
            keyword = str(row.get("keyword") or "当天重点").strip()
            seed = f"今天围绕“{keyword}”安排一个可调整的小步。"
            if isinstance(actions, list):
                for action in sorted((a for a in actions if isinstance(a, str) and a.strip()), key=len):
                    fragment = _compact_action_fragment(action.strip(), 60 - len(seed) - 1)
                    candidate = f"{seed}{fragment}。" if fragment else ""
                    if 30 <= len(candidate) <= 60:
                        row["summary"] = candidate
                        changes.append({"entry_date": row.get("entry_date"), "field": "summary", "before": raw_summary,
                            "after": candidate, "rule": "create_summary_from_keyword_and_action"})
                        before = candidate
                        break
            if not before:
                candidate = f"{seed}先记录当天感受，再决定下一步。"
                if 30 <= len(candidate) <= 60:
                    row["summary"] = candidate
                    changes.append({"entry_date": row.get("entry_date"), "field": "summary", "before": raw_summary,
                        "after": candidate, "rule": "create_summary_from_keyword"})
                    before = candidate
        if not before or len(before) >= 30:
            continue
        if not isinstance(actions, list):
            continue
        for action in sorted((a for a in actions if isinstance(a, str) and a.strip()), key=len):
            combined = f"{before.rstrip('。')}。{action.strip().rstrip('。')}。"
            if 30 <= len(combined) <= 60:
                row["summary"] = combined
                changes.append({"entry_date": row.get("entry_date"), "field": "summary", "before": before,
                    "after": combined, "rule": "append_existing_suitable_action"})
                break
            fragment = _compact_action_fragment(action.strip(), 60 - len(before.rstrip("。")) - 1)
            if fragment:
                combined = f"{before.rstrip('。')}，{fragment}。"
                if 30 <= len(combined) <= 60:
                    row["summary"] = combined
                    changes.append({"entry_date": row.get("entry_date"), "field": "summary", "before": before,
                        "after": combined, "rule": "append_existing_suitable_action_clause"})
                    break
    return changes


def diversify_duplicate_awareness(rows, previous_rows=()):
    """Replace a repeated awareness question with a complete contextual question."""
    seen = {}
    changes = []
    for row in previous_rows:
        text = row.get("energy_awareness") if isinstance(row, dict) else None
        if isinstance(text, str) and text.strip():
            seen[" ".join(text.split()).casefold()] = row.get("entry_date")
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("energy_awareness")
        if not isinstance(text, str) or not text.strip():
            continue
        normalized = " ".join(text.split()).casefold()
        if normalized not in seen:
            seen[normalized] = row.get("entry_date")
            continue
        keyword = str(row.get("keyword") or "当天情境").strip()
        summary = str(row.get("summary") or "").strip()
        context = next((part.strip() for part in re.split(r"[。！？]", summary) if part.strip()), keyword)
        context = context[:24].rstrip("，。；：")
        updated = f"围绕“{keyword}”的{context}，你准备先观察哪一个具体变化？"
        row["energy_awareness"] = updated
        changes.append({"entry_date": row.get("entry_date"), "field": "energy_awareness", "before": text,
            "after": updated, "rule": "differentiate_duplicate_energy_awareness"})
        seen[" ".join(updated.split()).casefold()] = row.get("entry_date")
    return changes


def diversify_repeated_suitable(rows, previous_rows=()):
    """Give repeated scheduled actions a concrete, staged observation point."""
    seen = {}
    changes = []
    progression = [
        "记录执行前最明显的阻力。",
        "记录执行时对方或环境的反馈。",
        "记录完成后的结果与需要调整的地方。",
        "复盘今天的记录，决定下一次如何微调。",
    ]
    progression_keys = {
        item.rstrip("。 ").casefold(): item
        for item in progression
    }

    def normalize_action(action, count):
        parts = [part.strip() for part in re.split(r"[；;]", action) if part.strip()]
        if not parts:
            return action
        base = parts[0]
        extras = []
        seen_parts = set()
        for part in parts[1:]:
            key = part.rstrip("。 ").casefold()
            if key in seen_parts:
                continue
            seen_parts.add(key)
            extras.append(part)

        repeated_stages = [
            progression_keys[key]
            for key in seen_parts
            if key in progression_keys
        ]
        custom_extras = [
            part for part in extras
            if part.rstrip("。 ").casefold() not in progression_keys
        ]
        if count and not custom_extras:
            extras = [progression[(count - 1) % len(progression)]]
        elif repeated_stages:
            extras = custom_extras + [repeated_stages[0]]

        normalized = "；".join([base, *extras]) if extras else base
        if normalized == action:
            return action
        return normalized.rstrip("。 ") + "。"

    for source in previous_rows:
        if not isinstance(source, dict):
            continue
        actions = source.get("suitable")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, str) or not action.strip():
                continue
            normalized = " ".join(action.split("；", 1)[0].split()).casefold()
            seen[normalized] = seen.get(normalized, 0) + 1
    for source in rows:
        if not isinstance(source, dict):
            continue
        actions = source.get("suitable")
        if not isinstance(actions, list):
            continue
        for index, action in enumerate(actions):
            if not isinstance(action, str) or not action.strip():
                continue
            normalized = " ".join(action.split("；", 1)[0].split()).casefold()
            count = seen.get(normalized, 0)
            updated = normalize_action(action, count)
            if updated != action:
                actions[index] = updated
                changes.append({"entry_date": source.get("entry_date"), "field": f"suitable.{index}",
                    "before": action, "after": updated, "rule": "stage_repeated_scheduled_action"})
            seen[normalized] = count + 1
    return changes


async def produce_calendar(db, request, *, gateway=None):
    snapshot = deepcopy(request.input_snapshot or {})
    report = snapshot.get("source_report") or {}
    foundation = report.get("reviewed_foundation") or {}
    temporal = calculate_temporal_facts(request.start_date, foundation)
    bindings = snapshot.get("calendar_skill_bindings")
    if not bindings:
        bindings = await freeze_calendar_skills(db)
    snapshot.update(calendar_skill_bindings=bindings, temporal_facts=temporal)
    request.input_snapshot = snapshot
    await db.commit()
    fact_by_date = {f["entry_date"]: f for f in temporal["days"]}
    all_dates = list(fact_by_date)
    batches = [all_dates[i:i + 10] for i in range(0, 30, 10)]
    base = {**calendar_model_context(snapshot, temporal),
            "current_request": {"focus_topics": request.focus_topics, "goal": request.goal,
                "usage_scenario": request.usage_scenario, "decision_description": request.decision_description,
                "additional_info": request.additional_info, "expected_outcomes": request.expected_outcomes,
                "available_minutes_per_day": snapshot.get("available_minutes_per_day", 30),
                "start_date": request.start_date.isoformat(), "end_date": request.end_date.isoformat()}}
    practice_rhythm = deepcopy(report.get("practice_rhythm") or {"actions": [], "unavailable_actions": []})
    available_minutes = snapshot.get("available_minutes_per_day", 30)
    require_action_refs = "practice_rhythm" in report
    practice_schedule, schedule_unavailable = plan_practice_schedule(
        practice_rhythm, all_dates, available_minutes
    )
    practice_rhythm["unavailable_actions"].extend(schedule_unavailable)
    base["practice_schedule"] = practice_schedule
    runs = []
    all_runs = []
    total_runs = 8
    attempt = (snapshot.get("generation") or {}).get("attempt", 1)

    async def run(key, suffix, extra, validator):
        nonlocal total_runs
        binding = bindings[key]
        version = await db.get(AISkillVersion, binding["id"])
        if version is None or version.status != "PUBLISHED" or version.skill_key != key or specification_digest(version.specification_json) != binding["sha256"]:
            raise ValueError("calendar_skill_version_unavailable")
        inputs = {**deepcopy(base), **extra}
        if "requested_dates" in extra:
            inputs["temporal_facts"]["days"] = [f for f in inputs["temporal_facts"]["days"] if f["entry_date"] in extra["requested_dates"]]
            if "temporal_analysis" in inputs:
                inputs["temporal_analysis"] = [a for a in inputs["temporal_analysis"] if a["entry_date"] in extra["requested_dates"]]
            if "practice_schedule" in inputs:
                inputs["practice_schedule"] = {
                    day: refs for day, refs in inputs["practice_schedule"].items()
                    if day in extra["requested_dates"]
                }
        if key == "calendar.daily_authoring" and "requested_dates" in extra:
            scoped_report, scheduled_by_date = project_scheduled_actions_for_authoring(
                inputs.get("source_report"), inputs.get("practice_schedule"), extra["requested_dates"]
            )
            inputs["source_report"] = scoped_report
            inputs["scheduled_practice_by_date"] = scheduled_by_date
        runtime_instruction = extra.get("format_repair_instruction")
        quality_codes = {
            item.get("code") for item in (extra.get("quality_feedback") or [])
            if isinstance(item, dict)
        }
        if extra.get("quality_feedback"):
            runtime_instruction = (runtime_instruction or "") + (
                "\n独立校准反馈是本次重写的硬性问题清单：只改requested_dates中被反馈点名的实际文案，"
                "逐项按field_path修复并保留action_refs、tone、day_pillar、windows.period和固定来源。"
                "每个日期仍须保留2–3条非空suitable；被反馈点名的suitable条目若引用了未排入当日的报告练习，"
                "改写为不调用报告Action的日常安排，不得直接删除条目或让数组短于2条。"
                "不要只解释问题，也不要把approved改为true绕过问题。"
            )
        if quality_codes & {"REPETITIVE_DAILY_ADVICE", "REPETITIVE_SUGGESTION"}:
            runtime_instruction = (runtime_instruction or "") + (
                "\n独立校准指出逐日建议重复：必须逐项改写反馈列出的日期的suitable文案，"
                "让相邻日期使用不同现实情境、观察点或递进任务；保留当天action_refs及其原顺序，"
                "不得添加未排入的报告Action，也不能只替换日期。"
            )
        if quality_codes & {"MONTH_REPETITION", "MONTH_REPETITION_NO_PROGRESSION"}:
            runtime_instruction = (runtime_instruction or "") + (
                "\n独立校准指出行动缺少递进：相同action_refs可以继续排入，但每个日期的suitable必须结合当天summary或keyword，"
                "明确不同情境、反馈记录或下一步，不得逐字复制其他日期的行动句。"
            )
        if quality_codes & {"FACT_CONFLICT", "FACT_CONFLICT_TIME_PILLAR", "TEN_GOD_ERROR", "TEN_GOD_MISLABEL", "SELF_CONTRADICTION_TEN_GOD"}:
            runtime_instruction = (runtime_instruction or "") + (
                "\n独立校准指出固定事实或术语冲突：逐字核对当天facts和windows，不得把流日干支当作时柱，"
                "不得自行补造时辰或十神；无法从facts确定时使用不带具体术语的日常表达。"
            )
        if "WINDOW_ACTION_MISMATCH" in quality_codes:
            runtime_instruction = (runtime_instruction or "") + (
                "\n独立校准指出窗口建议与行动不一致：只调整反馈列出的windows文案，使其对应当天已排入的action_refs，"
                "保留period、色块、day_pillar和其他固定事实。"
            )
        if runtime_instruction and "calendar_energy_awareness_repeated" in runtime_instruction:
            runtime_instruction += " 修改错误详情列出的energy_awareness，使问句贴合当天已有情境和观察点，且与其他日期不同；不可只替换日期或复用同一观察点。"
        if key == "calendar.calibration":
            analysis_map = {a["entry_date"]: a for a in inputs.pop("temporal_analysis")}
            facts_map = {f["entry_date"]: f for f in inputs["temporal_facts"].pop("days")}
            inputs["calendar_review_days"] = [{**e,
                "tone": analysis_map[e["entry_date"]]["tone"],
                "day_pillar": facts_map[e["entry_date"]]["day_pillar"],
                "analysis": {**{k: v for k, v in analysis_map[e["entry_date"]].items() if k != "windows"},
                    "selected_window_periods": [w["period"] for w in analysis_map[e["entry_date"]]["windows"]]},
                "facts": {**facts_map[e["entry_date"]], "windows": [w for w in facts_map[e["entry_date"]]["windows"]
                    if w["period"] in {a["period"] for a in analysis_map[e["entry_date"]]["windows"]}]} }
                for e in inputs.pop("entries")]
            inputs["programmatic_checks"] = {
                "dates_complete_and_unique": True, "analysis_dimensions_present_and_in_range": True,
                "source_reference_keys_valid": True, "weighted_colors_fixed": True,
                "selected_window_periods_valid": True, "daily_structure_valid": True,
                "scope": "程序检查字段、引用标识与固定时序；请审核具体解释和用户文案的实质一致性。"}
        examples = (snapshot.get("calendar_examples") or {}).get(key)
        if examples is None:
            policy = version.specification_json.get("example_policy") or {}
            examples = await retrieve_skill_examples(db, skill_key=key, target_key=None, context=base["current_request"],
                        max_examples=policy.get("max_examples", 3) if policy.get("enabled") else 0)
        inputs["few_shot_examples"] = examples
        log, _ = await create_skill_run(db, skill_version_id=version.id,
            idempotency_key=f"calendar:{request.id}:{attempt}:{key}:{suffix}",
            input_snapshot=inputs, context_snapshot={"calendar_request_id": request.id,
                "source_report_id": request.source_report_id, "skill_key": key},
            target_type="CALENDAR_PRODUCTION", target_key=str(request.id), report_case_id=report.get("report_case_id"),
            selected_examples=examples, run_type="VALIDATE" if key.endswith("calibration") else "INITIAL")
        log.runtime_instruction = runtime_instruction
        all_runs.append(log.id)
        if log.status == "COMPLETED":
            validator(log.output_parsed)
            runs.append(log.id)
            return log.output_parsed
        log.status, log.started_at = "RUNNING", utc_now_naive()
        progress = dict(request.input_snapshot or {})
        progress["generation"] = {**(progress.get("generation") or {}), "status": "RUNNING", "attempt": attempt, "stage": key,
                                  "heartbeat_at": utc_now_iso(),
                                  "completed_runs": len(all_runs) - 1, "total_runs": total_runs}
        request.input_snapshot = progress
        await db.commit()
        execution_error = None
        try:
            result = await execute_skill(skill_version=version, input_data=inputs, gateway=gateway,
                runtime_instruction=runtime_instruction)
            log.output_raw, log.output_parsed = result.output_raw, result.output_parsed
            log.model_trace = result.model_trace
            log.context_snapshot = {**result.context_snapshot, "calendar_request_id": request.id, "source_report_id": request.source_report_id, "skill_key": key}
            if key == "calendar.daily_authoring":
                previous_rows = [row for row in (extra.get("calendar_action_overview") or [])
                    if row.get("entry_date") not in (extra.get("requested_dates") or [])]
                normalizations = complete_short_summaries(result.output_parsed)
                if extra.get("format_repair_instruction"):
                    normalizations.extend(diversify_duplicate_awareness(result.output_parsed.get("entries", []), previous_rows))
                normalizations.extend(diversify_repeated_suitable(result.output_parsed.get("entries", []), previous_rows))
                log.context_snapshot = {**log.context_snapshot, "normalizations": normalizations}
            validator(result.output_parsed)
            log.status = "COMPLETED"
        except Exception as error:
            log.status = "FAILED"
            log.error = str(error) if isinstance(error, ValueError) else "calendar_model_failed"
            if isinstance(error, SkillExecutionError):
                log.model_trace = error.model_trace
                log.output_raw = error.output_raw
            execution_error = error
        finally:
            log.completed_at = utc_now_naive()
            await db.commit()
        if execution_error is not None:
            if isinstance(execution_error, ValueError) and not extra.get("format_repair_instruction") and str(execution_error) not in {
                "calendar_calibration_blocked", "skill_provider_request_failed", "skill_guardrail_blocked"}:
                total_runs += 1
                summary_feedback = json.dumps([
                    {"entry_date": e.get("entry_date"), "characters": len(e.get("summary") or "")}
                    for e in (log.output_parsed or {}).get("entries", [])
                ], ensure_ascii=False)
                suitable_feedback = json.dumps([
                    {"entry_date": e.get("entry_date"),
                     "count": len(e["suitable"]) if isinstance(e.get("suitable"), list) else None}
                    for e in (log.output_parsed or {}).get("entries", [])
                ], ensure_ascii=False)
                return await run(key, suffix + ":repair", {**extra,
                    "previous_output": log.output_parsed or log.output_raw,
                    "summary_character_counts": [{"entry_date": e.get("entry_date"), "characters": len(e.get("summary") or "")}
                        for e in (log.output_parsed or {}).get("entries", [])],
                    "suitable_counts": [{"entry_date": e.get("entry_date"),
                        "count": len(e["suitable"]) if isinstance(e.get("suitable"), list) else None}
                        for e in (log.output_parsed or {}).get("entries", [])],
                    "format_repair_instruction": f"上次输出未通过程序校验：{execution_error}。只修复结构或来源错误，重新返回本阶段完整JSON，不改变系统日期、干支、色块或窗口。若错误包含calendar_summary_length_invalid，必须把错误详情列出的日期摘要逐项改为30–60字；本批摘要长度参考：{summary_feedback}。若错误包含calendar_directions_invalid，逐日把suitable修回2–3条非空字符串（当日排入多个Action时上限为2+排入数量且不超过5），被点名引用未排入练习的条目改写为不调用报告Action的日常安排，不能删除到少于2条；本批suitable条数参考：{suitable_feedback}。若错误包含calendar_energy_awareness_repeated，必须改写后出现日期的energy_awareness，使其结合当天summary、keyword或action_refs提出不同观察问题，不得逐字复用历史日期问句。若错误包含calendar_practice_schedule_mismatch，逐日照抄错误详情中的expected数组，actual数组一律视为错误；不得添加未排入的报告Action，也不得在suitable中安排未排入行动的步骤。scheduled_practice_by_date是本批唯一可执行的报告行动清单，practice_schedule是最终排程。windows每项含period、label、suggestion；daily summary含标点目标35–45字符，必须30–60字符；keyword用顿号连接2–4词；source_refs只能用allowed_source_refs。逐日文案必须带action_refs数组，只能引用报告行动并遵守每日时间预算与频率。校准MAJOR/BLOCK必须给出field_path和observed_text逐字引用实际交付文案；只评文案，不重排或质疑固定facts，不把已核验字段说成缺失。不得通过把approved改为true绕过质量问题。"}, validator)
            raise execution_error
        runs.append(log.id)
        return result.output_parsed

    analyses = []
    references = {s.get("fragment_key") for s in report.get("structured_sections", [])}
    semantics = report.get("confirmed_semantics") or {}
    references.update(f.get("finding_key") for f in semantics.get("findings", []))
    references.update(e.get("evidence_key") for e in semantics.get("evidence", []))
    references.discard(None)
    if not references:
        references.add("source_report.summary")
    base["allowed_source_refs"] = sorted(references)
    weights = (await db.get(AISkillVersion, bindings["calendar.temporal_analysis"]["id"])).specification_json["instructions"]["tone_weights"]
    for batch_no, dates in enumerate(batches):
        def validate_analysis(output):
            require_dates(output.get("days"), dates)
            for item in output["days"]:
                if not item.get("psychological_theme") or not item.get("primary_theme") or not item.get("source_refs") or not set(item["source_refs"]) <= references:
                    raise ValueError("calendar_analysis_source_invalid")
                validate_windows(item.get("windows"), fact_by_date[item["entry_date"]])
                select_tone(item.get("dimensions") or {}, weights)
        output = await run("calendar.temporal_analysis", str(batch_no), {"requested_dates": dates, "allowed_source_refs": sorted(references)}, validate_analysis)
        for item in output["days"]:
            fact = fact_by_date[item["entry_date"]]
            tone, score = select_tone(item["dimensions"], weights, degraded=not fact["current_dayun"] or not foundation.get("bazi"))
            analyses.append({**item, "tone": tone, "weighted_score": score,
                             "degraded": not fact["current_dayun"] or not foundation.get("bazi")})
    analysis_by_date = {a["entry_date"]: a for a in analyses}
    base["temporal_analysis"] = analyses
    base["tone_weights"] = weights
    base["color_policy"] = {"labels": {"green": "推进", "blue": "探索", "yellow": "校准", "red": "收束"},
        "thresholds": {"green": ">=0.7", "blue": ">=0 and <0.7", "yellow": ">=-0.8 and <0", "red": "<-0.8"},
        "degraded": "缺少审核本命/适用大运时固定yellow；不能用主主题替代系统色块。"}
    def validate_monthly(output):
        monthly = output.get("monthly") or {}
        if any(not isinstance(monthly.get(k), str) or not monthly[k].strip() for k in (
            "direction", "growth_task", "resource", "old_pattern", "decision_principle", "rhythm_changes")):
            raise ValueError("calendar_monthly_incomplete")
    monthly = (await run("calendar.monthly_tone", "all", {}, validate_monthly))["monthly"]
    base["monthly"] = monthly
    def action_overview(rows):
        return [{k: row.get(k) for k in ("entry_date", "keyword", "suitable", "energy_awareness", "action_refs")} for row in rows]
    def validate_daily_batch(output, dates, previous_entries=()):
        require_dates(output.get("entries"), dates)
        mismatches = []
        for entry in output["entries"]:
            day = entry["entry_date"]
            expected = practice_schedule[day]
            actual = entry.get("action_refs")
            if actual != expected:
                mismatches.append({"entry_date": day, "expected": expected, "actual": actual})
            canonical = {**entry, "action_refs": expected}
            validate_daily(canonical, analysis_by_date[day], fact_by_date[day],
                practice_rhythm=practice_rhythm, available_minutes_per_day=available_minutes,
                scheduled_refs=expected, require_action_refs=require_action_refs)
        validate_unique_daily_awareness(
            output["entries"],
            [row for row in previous_entries if row.get("entry_date") not in dates],
        )
        if mismatches:
            raise ValueError("calendar_practice_schedule_mismatch:" + json.dumps(mismatches, ensure_ascii=False, separators=(",", ":")))

    entries = []
    for batch_no, dates in enumerate(batches):
        def validate_entries(output):
            validate_daily_batch(output, dates, entries)
        entries.extend((await run("calendar.daily_authoring", str(batch_no),
            {"requested_dates": dates, "calendar_action_overview": action_overview(entries)}, validate_entries))["entries"])
    original = {e["entry_date"]: e for e in entries}
    def validate_calibration(output):
        if not isinstance(output.get("patches"), list) or not isinstance(output.get("issues"), list):
            raise ValueError("calendar_calibration_invalid")
        for issue in output["issues"]:
            if not isinstance(issue, dict) or issue.get("severity") not in {"BLOCK", "MAJOR", "MINOR"}:
                raise ValueError("calendar_calibration_invalid")
            if issue["severity"] in {"BLOCK", "MAJOR"}:
                field = issue.get("field_path") or ""
                quote = issue.get("observed_text")
                if not isinstance(field, str) or not isinstance(quote, str) or not quote.strip():
                    raise ValueError("calendar_calibration_evidence_invalid")
                if field.startswith("monthly."):
                    value = monthly
                    parts = field.split(".")[1:]
                else:
                    value = original.get(issue.get("entry_date"))
                    parts = field.split(".")
                    if parts[0] not in {"summary", "suitable", "unsuitable", "energy_awareness", "tone_explanation", "windows"}:
                        raise ValueError("calendar_calibration_evidence_invalid")
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
                        value = value[int(part)]
                    else:
                        value = None
                if value is None or quote not in (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)):
                    raise ValueError("calendar_calibration_evidence_invalid")
        # Rejected review patches are never applied. Preserve the issues and
        # rewrite through the authoring skill instead of repairing discarded prose.
        if output.get("approved") is not True:
            raise ValueError("calendar_calibration_blocked")
        seen = set()
        for patch in output["patches"]:
            day = patch.get("entry_date")
            if day not in original or day in seen:
                raise ValueError("calendar_calibration_invalid")
            validate_daily(patch, analysis_by_date[day], fact_by_date[day],
                practice_rhythm=practice_rhythm, available_minutes_per_day=available_minutes,
                scheduled_refs=practice_schedule[day], require_action_refs=require_action_refs)
            seen.add(day)
        for issue in output["issues"]:
            if issue["severity"] in {"BLOCK", "MAJOR"} and (
                issue["field_path"].startswith("monthly.") or issue.get("entry_date") not in seen
            ):
                raise ValueError("calendar_calibration_blocked")
    for review_round in range(3):
        try:
            calibration = await run("calendar.calibration", f"all:{review_round}", {"entries": list(original.values())}, validate_calibration)
            break
        except ValueError as error:
            log = await db.get(SkillRun, all_runs[-1])
            feedback = (log.output_parsed or {}).get("issues") or []
            if str(error) != "calendar_calibration_blocked" or review_round == 2 or not feedback or any(i.get("severity") == "BLOCK" for i in feedback):
                raise
            # Repair prose based on independent review, then review the entire month again.
            # Scores, sources and windows remain fixed; unresolved quality never publishes.
            monthly_feedback = [i for i in feedback if i["severity"] == "MAJOR" and i["field_path"].startswith("monthly.")]
            daily_feedback = [i for i in feedback if i["severity"] == "MAJOR" and not i["field_path"].startswith("monthly.")]
            total_runs += 1 + bool(monthly_feedback) + (3 if daily_feedback else 0)
            if monthly_feedback:
                monthly = (await run("calendar.monthly_tone", f"review:{review_round}",
                    {"quality_feedback": monthly_feedback, "previous_monthly": monthly,
                     "revision_scope": "修正被独立校准指出的月度文案。日期色块以temporal_analysis为准，返回完整monthly。"},
                    validate_monthly))["monthly"]
                base["monthly"] = monthly
            for batch_no, dates in enumerate(batches if daily_feedback else []):
                def validate_rewrite(output):
                    validate_daily_batch(output, dates, original.values())
                rewritten = await run("calendar.daily_authoring", f"review:{review_round}:{batch_no}",
                    {"requested_dates": dates, "quality_feedback": daily_feedback,
                     "calendar_action_overview": action_overview(original.values()),
                     "previous_entries": [original[d] for d in dates]}, validate_rewrite)
                original.update({e["entry_date"]: e for e in rewritten["entries"]})
    else:
        raise ValueError("calendar_calibration_blocked")
    for patch in calibration["patches"]:
        original[patch["entry_date"]] = patch
    final = [original[d] for d in all_dates]
    validate_practice_schedule(final, practice_rhythm, available_minutes, practice_schedule)
    if len({e["summary"].strip() for e in final}) != 30:
        raise ValueError("calendar_repeated_content")
    for index in range(21):
        if len({json.dumps(e["suitable"], ensure_ascii=False) for e in final[index:index + 10]}) == 1:
            raise ValueError("calendar_repeated_guidance")
    labels = {"green": "推进", "blue": "探索", "yellow": "校准", "red": "收束"}
    output_entries = [{**e, "tone": analysis_by_date[e["entry_date"]]["tone"],
        "day_pillar": fact_by_date[e["entry_date"]]["day_pillar"],
        "status_label": labels[analysis_by_date[e["entry_date"]]["tone"]],
        "time_window": "\n".join(f'{w["period"]}｜{w["label"]}：{w["suggestion"]}' for w in e["windows"]),
        "admin_note": None} for e in final]
    payload = {"title": "辰鉴·30天决策日历", "start_date": all_dates[0], "end_date": all_dates[-1],
        "meta_payload": {"intro": monthly["direction"], "rhythm": monthly["rhythm_changes"],
            "overview": list(monthly.values()), "monthly": monthly, "limitations": temporal["limitations"],
            "source_report_id": request.source_report_id, "source_report_version_id": report.get("report_version_id"),
            "practice_rhythm": practice_rhythm, "available_minutes_per_day": available_minutes,
            "daily_details": {e["entry_date"]: {k: e[k] for k in ("energy_awareness", "tone_explanation", "windows", "action_refs")} for e in final}},
        "entries": output_entries}
    data = validate_generated_calendar(payload, {"start_date": all_dates[0], "end_date": all_dates[-1]})
    end_snapshot = dict(request.input_snapshot or {})
    end_snapshot["production_trace"] = {"skill_run_ids": all_runs, "temporal_analysis": analyses, "monthly": monthly,
                                        "calibration": calibration, "tone_weights": weights,
                                        "practice_schedule": practice_schedule,
                                        "available_minutes_per_day": available_minutes}
    request.input_snapshot = end_snapshot
    await db.commit()
    return data
