from app.policy import validate
from app.schemas import SchedulingCase


def case(msg, reply, status="confirmed", crew="confirmed", slots=None, jobs=None, date="2026-10-13"):
    return SchedulingCase.model_validate({
        "customer_message": msg, "appointment": {"date": date, "status": status},
        "crew": {"confirmation_status": crew}, "available_slots": slots or [], "other_jobs": jobs or [],
        "proposed_decision": {"action": "reply", "reply": reply}})


def rules(c):
    return [f.rule_id for f in validate(c, c.proposed_decision)]
