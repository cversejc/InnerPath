from app.application.report_analysis import build_analysis_completion_gate


def test_analysis_completion_requires_confirmed_output():
    gate = build_analysis_completion_gate(
        finding_statuses=[],
        fragment_statuses=[],
    )

    assert not gate["can_complete"]
    assert gate["blockers"] == ["report_analysis_output_required"]


def test_analysis_completion_blocks_unreviewed_and_stale_assets():
    gate = build_analysis_completion_gate(
        finding_statuses=["CONFIRMED", "PROPOSED"],
        fragment_statuses=["CONFIRMED", "PROPOSED", "STALE"],
    )

    assert not gate["can_complete"]
    assert gate["blockers"] == [
        "report_analysis_findings_unreviewed",
        "report_analysis_fragments_unreviewed",
        "report_analysis_fragments_stale",
    ]


def test_analysis_completion_passes_after_review():
    gate = build_analysis_completion_gate(
        finding_statuses=["CONFIRMED", "REJECTED"],
        fragment_statuses=["CONFIRMED"],
    )

    assert gate["can_complete"]
    assert gate["confirmed_finding_count"] == 1
    assert gate["confirmed_fragment_count"] == 1
    assert gate["blockers"] == []
