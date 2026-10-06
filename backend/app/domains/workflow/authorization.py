"""Shared professional ownership rules for HTTP and background use cases."""
from sqlalchemy import or_

from app.domains.service_requests.models import ServiceRequest


STEP_SPECIALTIES = {
    "S1": "mingli", "S2": "mingli", "S3": "mingli",
    "S4": "psychology", "S5": "psychology", "S6": "psychology",
}
SPECIALTY_FIELDS = {
    "mingli": "assigned_mingli_consultant_id",
    "psychology": "assigned_psychology_consultant_id",
}


def consultant_capabilities(consultant):
    capabilities = set()
    consultant_type = getattr(consultant, "consultant_type", None)
    if consultant_type in SPECIALTY_FIELDS:
        capabilities.add(consultant_type)
    elif consultant_type == "integrated":
        capabilities.update(SPECIALTY_FIELDS)

    for specialty in getattr(consultant, "consultant_specialties", None) or []:
        if specialty in SPECIALTY_FIELDS:
            capabilities.add(specialty)
        elif specialty == "metaphysics":
            capabilities.add("mingli")
    return capabilities


def assignment_condition(staff_id):
    return or_(
        ServiceRequest.assigned_consultant_id == staff_id,
        ServiceRequest.assigned_mingli_consultant_id == staff_id,
        ServiceRequest.assigned_psychology_consultant_id == staff_id,
    )


def is_assigned(request, staff_id):
    return staff_id in (
        request.assigned_consultant_id,
        getattr(request, "assigned_mingli_consultant_id", None),
        getattr(request, "assigned_psychology_consultant_id", None),
    )


def validate_step_actor(step, actor):
    if actor.role == "admin":
        return
    if actor.role != "consultant" or getattr(actor, "is_active", True) is False:
        raise ValueError("report_case_forbidden")
    capability = getattr(step, "required_capability", None)
    if capability and capability not in {*SPECIALTY_FIELDS, "consultant"}:
        raise ValueError("step_specialty_required")
    if capability in SPECIALTY_FIELDS:
        if capability not in consultant_capabilities(actor):
            raise ValueError("step_specialty_required")
        if step.assignee_id != actor.id:
            raise ValueError("step_assigned_to_another_consultant")
    elif step.assignee_id not in (None, actor.id):
        raise ValueError("step_assigned_to_another_consultant")
