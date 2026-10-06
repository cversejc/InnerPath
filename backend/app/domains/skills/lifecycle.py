"""Retired skill identities are preserved for history, never for new work."""
from sqlalchemy import select

from .models import AISkillVersion


RETIRED_SKILL_KEYS = frozenset({"report.generate"})


def require_active_skill(skill_key: str) -> None:
    if skill_key in RETIRED_SKILL_KEYS:
        raise ValueError("skill_retired")


async def retire_legacy_skills(db) -> None:
    versions = await db.scalars(select(AISkillVersion).where(
        AISkillVersion.skill_key.in_(RETIRED_SKILL_KEYS),
        AISkillVersion.status != "RETIRED",
    ).with_for_update())
    for version in versions:
        version.status = "RETIRED"
    await db.flush()
