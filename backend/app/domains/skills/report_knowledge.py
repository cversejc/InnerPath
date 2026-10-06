"""Versioned references from the same framework as the editable guidance."""
from .framework_guidance import framework_reference, framework_source


# Reference tables retain the framework's own columns and text. They are
# symbolic exploration aids; the framework's interpretation discipline applies.
TEN_GODS = framework_reference("ten_gods")
STARS = framework_reference("stars")
_STAGE_SKILLS = {
    "S1": "report.s1_foundation_analysis",
    "S2": "report.s2_psychology_mapping",
    "S3": "report.s3_integration",
    "S4": "report.s4_mechanism_block_action",
    "S5": "report.fragment_authoring",
}


def knowledge_for_stage(step_key):
    source = framework_source(_STAGE_SKILLS[step_key])
    reference = {"key": f"product-framework-{step_key.lower()}", **source}
    if step_key == "S2":
        reference.update(ten_gods=framework_reference("ten_gods"),
                         stars=framework_reference("stars"))
    elif step_key == "S3":
        reference["quadrants"] = framework_reference("quadrants")
    elif step_key == "S5":
        # The framework requests an approved quote library. Preserve the
        # existing verified entry; guidance does not create new attributions.
        reference["quote_library"] = [{
            "key": "laozi-33-self-knowledge", "text": "知人者智，自知者明。",
            "attribution": "《道德经》第三十三章",
            "source_url": "https://ctext.org/dao-de-jing/zh",
            "status": "VERIFIED", "verified_on": "2026-10-04",
        }]
    return [reference]
