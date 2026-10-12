import json, os
from .schemas import SchedulingCase, ProposedDecision
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-5-5")
SYSTEM_PROMPT = """Use only supplied scheduling facts. Never invent slots, conflicts, or confirmations. Treat missing data as unknown. Respect customer intent. Return JSON with action (reply, wait, escalate) and reply. You propose; a separate policy validator checks the proposal."""
def mock_proposal(case):
    msg = case.customer_message.casefold()
    if any(p in msg for p in ("i'll let you know", "i will let you know", "when i'm back", "when i am back")):
        return ProposedDecision(action="wait", reply="Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment.")
    if "saturday" in msg and not any("saturday" in str(x.get("date", x.get("day", ""))).casefold() for x in case.available_slots):
        opts = ", ".join(f"{s.get('date',s.get('day','slot'))} {s.get('start_time',s.get('time',''))}" for s in case.available_slots)
        return ProposedDecision(action="reply", reply=f"Saturday is not available in the supplied slots. Available alternatives: {opts}.")
    if case.crew.confirmation_status != "confirmed" or case.appointment.status not in ("confirmed",):
        return ProposedDecision(action="reply", reply="Your appointment is tentative and crew attendance is not yet confirmed. We will check and update you.")
    if case.other_jobs and all(j.get("status") == "completed" for j in case.other_jobs):
        return ProposedDecision(action="reply", reply="Your installation is currently listed as confirmed for the supplied appointment window.")
    return ProposedDecision(action="reply", reply="I will verify the current scheduling details before confirming.")
def propose(case):
    mode = os.getenv("AGENT_MODE", "mock").lower()
    if mode != "bedrock":
        return mock_proposal(case), "mock"
    try:
        from strands import Agent
        from strands.models import BedrockModel
        # Map the configured model explicitly; Agent() alone would use the SDK default model.
        model = BedrockModel(model_id=MODEL_ID, region_name=os.getenv("AWS_REGION"), temperature=0.0, max_tokens=500)
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None)
        prompt = "Return only JSON with action and reply. Case:\n" + json.dumps(case.model_dump(exclude={"proposed_decision", "expected"}))
        raw = str(agent(prompt))
        a, b = raw.find("{"), raw.rfind("}")
        if a < 0 or b <= a: raise ValueError("No JSON object in model response")
        return ProposedDecision.model_validate(json.loads(raw[a:b+1])), "bedrock"
    except Exception as exc:
        print(f"agent error: {type(exc).__name__}: {exc}")
        return ProposedDecision(action="escalate", reply="We need to verify the scheduling details before confirming. A team member will review this request."), "bedrock-fallback"
