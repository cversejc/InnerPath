import pytest
from tests.test_skill_runtime import skill_db
from app.domains.skills.service import ensure_default_analysis_skill_versions
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
