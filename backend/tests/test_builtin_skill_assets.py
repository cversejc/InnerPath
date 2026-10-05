from copy import deepcopy

import pytest
from tests.test_skill_runtime import skill_db
from app.domains.skills.service import ensure_default_analysis_skill_versions, ensure_default_narrative_skill_versions
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
    await skill_db.flush()

    again = await ensure_default_narrative_skill_versions(skill_db)

    assert again[1].id == published.id
    assert again[1].status == "PUBLISHED"
    assert again[1].specification_json["reasoning_guidance"]["methodology"] == [
        "已审核的旧版逐段写作思路"
    ]
