from datetime import datetime

import pytest
from sqlalchemy import ARRAY, JSON, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.content.service import (
    create_content_fragment_revision,
    create_evidence_item,
    create_finding_revision,
    load_confirmed_case_semantics,
    retract_case_evidence,
    set_finding_status,
    sync_application_evidence,
)
from app.domains.workflow.models import ReportCase
from app.models.user import User


class SyncSessionAdapter:
    def __init__(self, session: Session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def get(self, model, identity):
        return self.session.get(model, identity)

    async def flush(self):
        self.session.flush()

    async def refresh(self, value):
        self.session.refresh(value)


@pytest.fixture
def content_db(monkeypatch):
    tables = [
        ReportCase.__table__,
        User.__table__,
        CaseEvidenceItem.__table__,
        FindingRevision.__table__,
        ContentFragmentRevision.__table__,
        NarrativePlan.__table__,
    ]
    for table in tables:
        for column in table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                monkeypatch.setattr(column, "type", JSON())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as session:
        db = SyncSessionAdapter(session)
        report_case = ReportCase(
            user_id=1,
            status="ACTIVE",
            application_snapshot={},
            application_submitted_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(report_case)
        session.flush()
        yield db, report_case.id
    engine.dispose()


@pytest.mark.asyncio
async def test_application_evidence_preserves_sources_and_is_idempotent(content_db):
    db, case_id = content_db
    snapshot = {
        "profile": {"gender": "female", "birth_year": 1992},
        "context": {"current_challenge": "Considering a career change."},
        "selected_topics": ["career"],
        "idempotency_key": "private-submit-key",
        "foundation_data": {"ai_guess": "must not become evidence"},
    }

    first = await sync_application_evidence(
        db, report_case_id=case_id, application_snapshot=snapshot
    )
    second = await sync_application_evidence(
        db, report_case_id=case_id, application_snapshot=snapshot
    )

    assert len(first) == len(second) == 4
    assert {item.source_type for item in first} == {"USER_PROVIDED"}
    assert {item.evidence_key for item in first} == {
        "input.profile.gender",
        "input.profile.birth_year",
        "input.context.current_challenge",
        "input.selected_topics",
    }
    assert all("ai_guess" not in item.source_ref for item in first)
    assert await db.scalar(select(func.count(CaseEvidenceItem.id))) == 4
    calculated = await create_evidence_item(
        db,
        report_case_id=case_id,
        evidence_key="calculated.bazi.chart",
        source_type="SYSTEM_CALCULATED",
        source_ref="mingli_foundation.bazi_chart",
        value={"day_master": "wood"},
    )
    assert calculated.source_type == "SYSTEM_CALCULATED"

    with pytest.raises(ValueError, match="evidence_key_immutable"):
        await create_evidence_item(
            db,
            report_case_id=case_id,
            evidence_key="input.profile.gender",
            source_type="USER_PROVIDED",
            source_ref="application_snapshot.profile.gender",
            value="male",
        )


async def _finding(db, case_id, *, status="CONFIRMED"):
    return await create_finding_revision(
        db,
        report_case_id=case_id,
        finding_key="psychology.stability_autonomy_tension",
        claim="The person may experience tension between stability and autonomy.",
        semantic_role="CONFLICT",
        confidence="MEDIUM",
        importance="HIGH",
        reportability="RECOMMENDED",
        status=status,
    )


async def _fragment(db, case_id, key, *, finding_refs=None, fragment_refs=None):
    return await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=key,
        fragment_type="ANALYSIS",
        title=key,
        content=f"Analysis for {key}.",
        status="CONFIRMED",
        finding_refs=finding_refs or [],
        fragment_refs=fragment_refs or [],
    )


@pytest.mark.asyncio
async def test_semantic_finding_change_stales_only_dependent_fragments(content_db):
    db, case_id = content_db
    await _finding(db, case_id)
    direct = await _fragment(
        db,
        case_id,
        "analysis.psychology.core",
        finding_refs=["psychology.stability_autonomy_tension"],
    )
    downstream = await _fragment(
        db,
        case_id,
        "analysis.integration.direction",
        fragment_refs=["analysis.psychology.core"],
    )
    unrelated = await _fragment(db, case_id, "analysis.action.rhythm")

    style = await create_finding_revision(
        db,
        report_case_id=case_id,
        finding_key="psychology.stability_autonomy_tension",
        claim="The person may feel pulled between security and independence.",
        edit_kind="STYLE",
    )
    assert style.semantic_revision == 1
    assert style.content_revision == 2
    await db.refresh(direct)
    await db.refresh(downstream)
    assert direct.status == downstream.status == "CONFIRMED"

    semantic = await create_finding_revision(
        db,
        report_case_id=case_id,
        finding_key="psychology.stability_autonomy_tension",
        claim="Autonomy is currently the stronger unmet need.",
        edit_kind="SEMANTIC",
    )
    assert semantic.semantic_revision == 2
    assert semantic.content_revision == 3
    await db.refresh(direct)
    await db.refresh(downstream)
    await db.refresh(unrelated)
    assert direct.status == "STALE"
    assert downstream.status == "STALE"
    assert direct.stale_reason == "semantic_dependency_changed:finding:psychology.stability_autonomy_tension"
    assert unrelated.status == "CONFIRMED"

    current_count = await db.scalar(
        select(func.count(FindingRevision.id)).where(
            FindingRevision.report_case_id == case_id,
            FindingRevision.finding_key == "psychology.stability_autonomy_tension",
            FindingRevision.is_current.is_(True),
        )
    )
    assert current_count == 1
    revisions = list(
        await db.scalars(
            select(FindingRevision)
            .where(
                FindingRevision.finding_key
                == "psychology.stability_autonomy_tension"
            )
            .order_by(FindingRevision.revision_no)
        )
    )
    assert [row.revision_no for row in revisions] == [1, 2, 3]
    assert [row.status for row in revisions] == [
        "SUPERSEDED",
        "SUPERSEDED",
        "CONFIRMED",
    ]
    assert [row.status for row in revisions] == ["SUPERSEDED", "SUPERSEDED", "CONFIRMED"]


@pytest.mark.asyncio
async def test_fragment_style_edit_does_not_stale_dependents_but_semantic_edit_does(
    content_db,
):
    db, case_id = content_db
    parent = await _fragment(db, case_id, "analysis.integration.self_direction")
    child = await _fragment(
        db,
        case_id,
        "analysis.action.next_step",
        fragment_refs=["analysis.integration.self_direction"],
    )

    style = await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=parent.fragment_key,
        content="A clearer expression of the same professional judgment.",
        edit_kind="STYLE",
    )
    assert style.semantic_revision == 1
    assert style.content_revision == 2
    await db.refresh(child)
    assert child.status == "CONFIRMED"

    semantic = await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=parent.fragment_key,
        content="The direction should prioritize a different underlying need.",
        edit_kind="SEMANTIC",
        status="CONFIRMED",
    )
    assert semantic.semantic_revision == 2
    assert semantic.content_revision == 3
    await db.refresh(child)
    assert child.status == "STALE"


@pytest.mark.asyncio
async def test_style_edit_can_confirm_a_proposed_fragment_without_semantic_change(content_db):
    db, case_id = content_db
    draft = await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key="analysis.integration.direction",
        fragment_type="ANALYSIS",
        title="发展方向",
        content="先列出希望保留的工作条件。",
        status="PROPOSED",
    )

    confirmed = await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=draft.fragment_key,
        fragment_type="ANALYSIS",
        title="发展方向",
        content="先列出希望保留的工作条件，再用一次短期尝试核对。",
        status="CONFIRMED",
        edit_kind="STYLE",
    )

    assert confirmed.status == "CONFIRMED"
    assert confirmed.edit_kind == "STYLE"
    assert confirmed.semantic_revision == draft.semantic_revision
    assert confirmed.content_revision == draft.content_revision + 1


@pytest.mark.asyncio
async def test_rejected_findings_are_not_confirmed_semantics(content_db):
    db, case_id = content_db
    await _finding(db, case_id, status="PROPOSED")
    assert (await load_confirmed_case_semantics(db, case_id))["findings"] == []
    with pytest.raises(ValueError, match="fragment_requires_confirmed_findings"):
        await create_content_fragment_revision(
            db,
            report_case_id=case_id,
            fragment_key="analysis.psychology.core",
            content="A confirmed fragment cannot cite a proposed judgment.",
            status="CONFIRMED",
            finding_refs=["psychology.stability_autonomy_tension"],
        )

    await set_finding_status(
        db,
        report_case_id=case_id,
        finding_key="psychology.stability_autonomy_tension",
        status="CONFIRMED",
    )
    assert len((await load_confirmed_case_semantics(db, case_id))["findings"]) == 1

    fragment = await _fragment(
        db,
        case_id,
        "analysis.psychology.core",
        finding_refs=["psychology.stability_autonomy_tension"],
    )
    await set_finding_status(
        db,
        report_case_id=case_id,
        finding_key="psychology.stability_autonomy_tension",
        status="REJECTED",
    )
    await db.refresh(fragment)
    semantic = await load_confirmed_case_semantics(db, case_id)
    assert semantic["findings"] == []
    assert fragment.status == "STALE"


@pytest.mark.asyncio
async def test_evidence_retraction_stales_findings_that_used_it(content_db):
    db, case_id = content_db
    evidence = await create_evidence_item(
        db,
        report_case_id=case_id,
        evidence_key="input.context.current_challenge",
        source_type="USER_PROVIDED",
        source_ref="application_snapshot.context.current_challenge",
        value="Considering a career change.",
    )
    await create_finding_revision(
        db,
        report_case_id=case_id,
        finding_key="psychology.change_readiness",
        claim="The user is considering a career transition.",
        semantic_role="PATTERN",
        status="CONFIRMED",
        evidence_refs=[evidence.evidence_key],
    )
    fragment = await _fragment(
        db,
        case_id,
        "analysis.psychology.change_readiness",
        finding_refs=["psychology.change_readiness"],
    )

    await retract_case_evidence(
        db,
        report_case_id=case_id,
        evidence_key=evidence.evidence_key,
        reason="The user withdrew this context.",
    )

    await db.refresh(fragment)
    await db.refresh(evidence)
    assert evidence.status == "RETRACTED"
    assert evidence.status_reason == "The user withdrew this context."
    assert fragment.status == "STALE"
    assert (await load_confirmed_case_semantics(db, case_id))["findings"] == []


@pytest.mark.asyncio
async def test_fragment_dependency_graph_rejects_cycles(content_db):
    db, case_id = content_db
    first = await _fragment(db, case_id, "analysis.first")
    await _fragment(db, case_id, "analysis.second", fragment_refs=[first.fragment_key])

    with pytest.raises(ValueError, match="fragment_dependency_cycle"):
        await create_content_fragment_revision(
            db,
            report_case_id=case_id,
            fragment_key=first.fragment_key,
            content="A cyclic dependency is not valid.",
            fragment_type="ANALYSIS",
            status="CONFIRMED",
            fragment_refs=["analysis.second"],
        )
