from copy import deepcopy

import pytest
from tests.test_skill_runtime import skill_db
from app.application.report_cases import ensure_collaborative_workflow_version
from app.application.skill_runtime import ensure_analysis_workflow_version
from app.domains.skills.service import (
    create_skill_draft,
    ensure_default_analysis_skill_versions,
    ensure_default_narrative_skill_versions,
    publish_skill_version,
    update_reasoning_guidance,
)
from app.domains.skills.examples import retrieve_skill_examples, retire_skill_example, create_example_revision, publish_skill_example, update_example_redaction


@pytest.mark.asyncio
async def test_builtins_are_retrieved_and_retirement_persists(skill_db):
    await ensure_default_analysis_skill_versions(skill_db)
    rows = await retrieve_skill_examples(skill_db, skill_key="report.s2_psychology_mapping", target_key=None, context={})
    assert len(rows) == 1
    await retire_skill_example(skill_db, rows[0]["example_id"])
    await ensure_default_analysis_skill_versions(skill_db)
    assert await retrieve_skill_examples(skill_db, skill_key="report.s2_psychology_mapping", target_key=None, context={}) == []


@pytest.mark.asyncio
async def test_studio_published_skill_is_used_instead_of_reset(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    version = versions[1]
    version.created_by = 1
    version.specification_json = {**version.specification_json, "instructions": {**version.specification_json["instructions"], "objective": "人工维护的目标"}}
    await skill_db.flush()
    again = await ensure_default_analysis_skill_versions(skill_db)
    assert again[1].id == version.id
    assert again[1].specification_json["instructions"]["objective"] == "人工维护的目标"


@pytest.mark.asyncio
async def test_s1_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    published = versions[0]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已发布的旧版思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_analysis_skill_versions(skill_db)

    assert again[0].id == published.id
    assert again[0].specification_json["reasoning_guidance"]["methodology"] == [
        "已发布的旧版思路"
    ]


@pytest.mark.asyncio
async def test_s2_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    published = versions[1]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已审核的旧版心理映射思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_analysis_skill_versions(skill_db)

    assert again[1].id == published.id
    assert again[1].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版心理映射思路"
    ]


@pytest.mark.asyncio
async def test_s3_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    published = versions[2]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已审核的旧版整合思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_analysis_skill_versions(skill_db)

    assert again[2].id == published.id
    assert again[2].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版整合思路"
    ]


@pytest.mark.asyncio
async def test_s4_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    published = versions[3]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已审核的旧版机制与行动思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_analysis_skill_versions(skill_db)

    assert again[3].id == published.id
    assert again[3].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版机制与行动思路"
    ]


@pytest.mark.asyncio
async def test_narrative_plan_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_narrative_skill_versions(skill_db)
    published = versions[0]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已审核的旧版报告主线思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_narrative_skill_versions(skill_db)

    assert again[0].id == published.id
    assert again[0].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版报告主线思路"
    ]


@pytest.mark.asyncio
async def test_fragment_authoring_default_thought_changes_do_not_publish_over_existing_version(skill_db):
    versions = await ensure_default_narrative_skill_versions(skill_db)
    published = versions[1]
    previous = deepcopy(published.specification_json)
    previous["reasoning_guidance"]["methodology"] = ["已审核的旧版逐段写作思路"]
    published.specification_json = previous
    published.published_by = 1
    await skill_db.flush()

    again = await ensure_default_narrative_skill_versions(skill_db)

    assert again[1].id == published.id
    assert again[1].status == "PUBLISHED"
    assert again[1].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版逐段写作思路"
    ]


@pytest.mark.asyncio
async def test_code_seed_updates_publish_current_default_without_overwriting_history(skill_db):
    versions = await ensure_default_analysis_skill_versions(skill_db)
    previous = versions[0]
    old_specification = deepcopy(previous.specification_json)
    old_specification["reasoning_guidance"]["methodology"] = ["旧代码默认思路"]
    previous.specification_json = old_specification
    await skill_db.flush()

    current = (await ensure_default_analysis_skill_versions(skill_db))[0]

    assert current.id != previous.id
    assert current.status == "PUBLISHED"
    assert current.specification_json["reasoning_guidance"]["methodology"] != [
        "旧代码默认思路"
    ]
    assert previous.specification_json["reasoning_guidance"]["methodology"] == [
        "旧代码默认思路"
    ]


@pytest.mark.asyncio
async def test_matching_system_draft_is_published_with_current_program_fields(skill_db):
    from app.domains.skills.definitions import default_analysis_skill_specifications

    published = (await ensure_default_analysis_skill_versions(skill_db))[0]
    outdated = deepcopy(published.specification_json)
    outdated["reasoning_guidance"]["methodology"] = ["旧代码默认思路"]
    published.specification_json = outdated
    await skill_db.flush()

    current_specification = default_analysis_skill_specifications()[0]
    draft = await create_skill_draft(
        skill_db,
        skill_key=published.skill_key,
        name=published.name,
        category=published.category,
        specification=current_specification,
        created_by=None,
    )

    current = (await ensure_default_analysis_skill_versions(skill_db))[0]

    assert current.id == draft.id
    assert current.status == "PUBLISHED"
    assert current.specification_json == current_specification


@pytest.mark.asyncio
async def test_analysis_workflow_rebinds_new_skill_version_for_new_cases(skill_db):
    workflow = await ensure_collaborative_workflow_version(skill_db)
    versions = await ensure_default_analysis_skill_versions(skill_db)
    old_skill = versions[0]
    draft = await create_skill_draft(
        skill_db,
        skill_key=old_skill.skill_key,
        name=old_skill.name,
        category=old_skill.category,
        specification=old_skill.specification_json,
        created_by=1,
    )
    await update_reasoning_guidance(
        skill_db,
        draft.id,
        objective="按最新已确认的命理基础结果形成可审阅的结构判断。",
        methodology=["依据输入证据说明结构判断，并标出资料边界。"],
    )
    await publish_skill_version(skill_db, draft.id, published_by=1)

    rebound = await ensure_collaborative_workflow_version(skill_db)

    assert rebound.id != workflow.id
    assert rebound.definition_json["collaboration_contract"] == workflow.definition_json[
        "collaboration_contract"
    ]
    assert rebound.definition_json["skill_bindings"][old_skill.skill_key]["id"] == draft.id
    assert rebound.definition_json["steps"][0]["config"]["skill_version_id"] == draft.id


@pytest.mark.asyncio
async def test_admin_workflow_keeps_its_explicit_skill_version_pin(skill_db):
    workflow = await ensure_collaborative_workflow_version(skill_db)
    versions = await ensure_default_analysis_skill_versions(skill_db)
    old_skill = versions[0]
    workflow.created_by = 1
    workflow.published_by = 1
    await skill_db.flush()

    draft = await create_skill_draft(
        skill_db,
        skill_key=old_skill.skill_key,
        name=old_skill.name,
        category=old_skill.category,
        specification=old_skill.specification_json,
        created_by=1,
    )
    await update_reasoning_guidance(
        skill_db,
        draft.id,
        objective="按已确认输入形成可审阅的命理基础判断。",
        methodology=["解释判断依据，并写明缺少资料时的边界。"],
    )
    await publish_skill_version(skill_db, draft.id, published_by=1)

    current = await ensure_collaborative_workflow_version(skill_db)

    assert current.id == workflow.id
    assert current.definition_json["skill_bindings"][old_skill.skill_key]["id"] == old_skill.id
