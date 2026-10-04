"""Project calendar-specific model context; keep the original snapshot in storage."""
from copy import deepcopy


def calendar_model_context(snapshot, temporal):
    source = snapshot.get("source_report") or {}
    foundation = source.get("reviewed_foundation") or {}
    semantics = source.get("confirmed_semantics") or {}
    reviewed = {k: deepcopy(foundation[k]) for k in ("bazi", "bazi_facts", "limitations", "assumptions") if k in foundation}
    facts = {k: deepcopy(v) for k, v in temporal.items() if k != "natal_foundation"}
    report = {k: deepcopy(source[k]) for k in ("id", "title", "summary", "report_version_id", "structured_sections") if k in source}
    report["structured_sections"] = [{k: deepcopy(v) for k, v in section.items() if k in
        {"fragment_key", "section_key", "section_title", "title", "content"}}
        for section in source.get("structured_sections", [])]
    report["reviewed_foundation"] = reviewed
    report["confirmed_semantics"] = {
        "findings": [{k: deepcopy(v) for k, v in f.items() if k in
            {"finding_key", "claim", "semantic_role", "confidence", "reportability", "evidence_refs", "finding_refs", "structured_analysis", "structured_data", "relation_refs"}}
            for f in semantics.get("findings", [])],
        "analysis_fragments": [{k: deepcopy(v) for k, v in f.items() if k in
            {"fragment_key", "title", "content", "structured_analysis", "finding_refs", "evidence_refs"}}
            for f in semantics.get("analysis_fragments", [])],
        "evidence": [{k: deepcopy(v) for k, v in e.items() if k in {"evidence_key", "source_type", "value"}
                      and not (k == "value" and e.get("source_type") == "SYSTEM_CALCULATED")}
            for e in semantics.get("evidence", [])],
    }
    return {"profile": deepcopy(snapshot.get("profile") or {}), "source_report": report,
            "questionnaire": deepcopy((source.get("application") or {}).get("context") or {}),
            "decision_feedback": deepcopy(snapshot.get("decision_feedback") or []), "temporal_facts": facts}
