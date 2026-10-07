"""Explicitly publish the current document-based defaults into an existing DB.

Preview: python -m tools.publish_skill_frameworks
Apply: python -m tools.publish_skill_frameworks --publish --replace-admin-guidance
Use the replacement flag only for an explicitly requested content reset.
Normal initialization continues to protect administrator-maintained skills.
"""
import argparse
import asyncio
from datetime import datetime
from app.core.time import utc_now_naive

from sqlalchemy import func, select

from app.application.report_cases import ensure_collaborative_workflow_version
from app.db.session import AsyncSessionLocal
from app.domains.calendar.skill_definitions import default_calendar_skill_specifications
from app.domains.skills.definitions import (
    default_analysis_skill_specifications,
    default_narrative_skill_specifications,
    default_validator_skill_specification,
)
from app.domains.skills.models import AISkillVersion


async def publish_current_frameworks(*, publish=False, replace_admin=False):
    definitions = [("ANALYSIS", spec) for spec in default_analysis_skill_specifications()]
    definitions.extend(("AUTHORING", spec) for spec in default_narrative_skill_specifications())
    definitions.append(("VALIDATOR", default_validator_skill_specification()))
    definitions.extend(default_calendar_skill_specifications())
    results = []
    async with AsyncSessionLocal() as db:
        for category, spec in definitions:
            key = spec["identity"]["skill_key"]
            latest = await db.scalar(select(AISkillVersion).where(
                AISkillVersion.skill_key == key, AISkillVersion.status == "PUBLISHED"
            ).order_by(AISkillVersion.version.desc()).limit(1))
            if latest is not None and latest.specification_json == spec:
                results.append((key, latest.version, "CURRENT"))
                continue
            if latest is not None and (latest.created_by is not None or latest.published_by is not None):
                if not replace_admin:
                    raise ValueError(f"Explicit administrator-guidance replacement required: {key}")
            maximum = await db.scalar(select(func.max(AISkillVersion.version)).where(
                AISkillVersion.skill_key == key)) or 0
            results.append((key, maximum + 1, "PUBLISHED" if publish else "PREVIEW"))
            if publish:
                now = utc_now_naive()
                # A fresh immutable publication preserves frozen cases/runs.
                # It uses current code contracts, not an old version's payload.
                db.add(AISkillVersion(skill_key=key, name=spec["identity"]["name"],
                    category=category, version=maximum + 1, status="PUBLISHED",
                    specification_json=spec, created_by=None, published_by=None,
                    created_at=now, published_at=now))
                await db.flush()
        if publish:
            workflow = await ensure_collaborative_workflow_version(db)
            await db.commit()
            results.append((workflow.workflow_key, workflow.version, workflow.status))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--replace-admin-guidance", action="store_true")
    args = parser.parse_args()
    results = asyncio.run(publish_current_frameworks(
        publish=args.publish, replace_admin=args.replace_admin_guidance))
    for key, version, status in results:
        print(f"{key}: v{version} {status}")


if __name__ == "__main__":
    main()
