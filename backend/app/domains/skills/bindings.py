"""Freeze the seven production skills at publication or case creation."""
from hashlib import sha256
import json

from .models import AISkillVersion
from .definitions import ANALYSIS_STEPS
from .lifecycle import require_active_skill
from .service import (
    ensure_default_analysis_skill_versions, ensure_default_narrative_skill_versions,
    ensure_default_validator_skill_version,
)

PRODUCTION_KEYS = {
    *(stage["skill_key"] for stage in ANALYSIS_STEPS.values()),
    "report.narrative_plan", "report.fragment_authoring", "report.final_validator",
}


def specification_digest(spec):
    return sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


async def _default_skill_bindings(db, required_keys):
    versions = [*await ensure_default_analysis_skill_versions(db),
                *await ensure_default_narrative_skill_versions(db),
                await ensure_default_validator_skill_version(db)]
    available = {version.skill_key: version.id for version in versions}
    if not required_keys.issubset(available):
        raise ValueError("case_skill_bindings_incomplete")
    return {key: version_id for key, version_id in available.items()
            if key in required_keys}


async def freeze_report_skills(db, bindings=None, steps=(), required_keys=None):
    """Freeze the skill versions a workflow binds to.

    ``required_keys`` defaults to the seven production skills so publications
    of ``report.production`` keep their existing contract.  The AI-assisted
    Simple protocol passes the six business skills its frozen definition
    declares and never binds ``report.narrative_plan``.
    """
    required = frozenset(required_keys) if required_keys is not None else PRODUCTION_KEYS
    explicitly_bound = bindings is not None
    if bindings is None:
        bindings = await _default_skill_bindings(db, required)
    if not isinstance(bindings, dict) or not required.issubset(bindings):
        raise ValueError("case_skill_bindings_incomplete")
    bindings = dict(bindings)
    for step in steps:
        config = step.get("config") or {}
        if config.get("skill_key"):
            require_active_skill(config["skill_key"])
        version_id = config.get("skill_version_id")
        if version_id is not None:
            version = await db.get(AISkillVersion, version_id)
            if version is None or config.get("skill_key", version.skill_key) != version.skill_key:
                raise ValueError("case_skill_binding_invalid")
            if version.skill_key in bindings:
                entry = bindings[version.skill_key]
                pinned_id = entry.get("id") if isinstance(entry, dict) else entry
                if pinned_id != version_id and explicitly_bound:
                    raise ValueError("case_skill_version_mismatch")
                if pinned_id == version_id:
                    continue
            bindings[version.skill_key] = version_id
    frozen = {}
    for key, entry in bindings.items():
        require_active_skill(key)
        version_id = entry.get("id") if isinstance(entry, dict) else entry
        if not isinstance(version_id, int) or isinstance(version_id, bool):
            raise ValueError("case_skill_binding_invalid")
        version = await db.get(AISkillVersion, version_id)
        if version is None or version.skill_key != key or version.status != "PUBLISHED":
            raise ValueError("case_skill_version_unavailable")
        record = {"id": version.id, "version": version.version,
                  "digest": specification_digest(version.specification_json)}
        if isinstance(entry, dict) and entry != record:
            raise ValueError("case_skill_binding_changed")
        frozen[key] = record
    return frozen


async def resolve_case_skill(db, case, skill_key):
    bindings = (case.application_snapshot or {}).get("skill_bindings")
    if bindings is None and case.review_policy_version == "six-node-review-v1":
        from sqlalchemy import select
        from app.domains.review.models import NodeReviewState
        state = await db.scalar(select(NodeReviewState).where(NodeReviewState.report_case_id == case.id, NodeReviewState.step_key == "S1"))
        bindings = (state.metadata_json or {}).get("runtime_skill_bindings") if state else None
    if bindings is None:
        # Historical cases retain the previous latest-published selection policy.
        bindings = await freeze_report_skills(db)
    if not isinstance(bindings, dict) or skill_key not in bindings:
        raise ValueError("case_skill_bindings_incomplete")
    entry = bindings[skill_key]
    if not isinstance(entry, dict) or not isinstance(entry.get("id"), int):
        raise ValueError("case_skill_binding_invalid")
    version = await db.get(AISkillVersion, entry["id"])
    if (version is None or version.status != "PUBLISHED" or version.skill_key != skill_key
            or entry != {"id": version.id, "version": version.version,
                         "digest": specification_digest(version.specification_json)}):
        raise ValueError("case_skill_binding_changed")
    return version
