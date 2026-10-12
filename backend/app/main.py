import json, os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import SchedulingCase, DecisionResponse
from .agent import propose
from .policy import validate
app=FastAPI(title="AI Scheduling Reliability API",version="0.1.0")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type"])
DATA=Path(__file__).resolve().parent.parent/"data"/"cases.json"
def load_cases(): return json.loads(DATA.read_text())
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/api/cases")
def cases(): return load_cases()
@app.post("/api/decide",response_model=DecisionResponse)
def decide(case:SchedulingCase):
    # If a proposal is supplied (fixture/evaluation/UI), validate that exact proposal.
    # For free-form requests without a proposal, ask the configured agent.
    if case.proposed_decision is not None:
        proposed, mode = case.proposed_decision, "supplied-proposal"
    else:
        proposed, mode = propose(case)
    findings=validate(case,proposed); ok=not findings
    return DecisionResponse(case_id=case.case_id,mode=mode,proposed_decision=proposed,acceptable=ok,findings=findings,
      final_action=proposed.action if ok else "escalate",
      final_reply=proposed.reply if ok else findings[0].safer_alternative,
      note="No real scheduling side effect is performed.")
@app.post("/api/evaluate")
def evaluate():
    from .evaluation import run_evaluation
    return run_evaluation()
@app.get("/api/report")
def report():
    from .evaluation import run_evaluation
    return run_evaluation()


# AWS Lambda entry point (API Gateway HTTP API) - same app, wrapped by Mangum.
from mangum import Mangum
handler = Mangum(app, lifespan="off")
