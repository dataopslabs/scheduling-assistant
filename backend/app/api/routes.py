from fastapi import APIRouter, HTTPException
from ..config import get_settings
from ..schemas import DecideRequest, DecisionResponse
from ..services import cases as case_repo
from ..services.decision import decide as run_decision

router = APIRouter()


@router.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "version": s.app_version}


@router.get("/api/config")
def config():
    s = get_settings()
    return {"model_id": s.model_id, "region": s.region, "modes": ["mock", "live"], "version": s.app_version}


@router.get("/api/cases")
def cases():
    return case_repo.list_cases()


@router.post("/api/decide", response_model=DecisionResponse)
def decide(req: DecideRequest):
    """mock: replay the fixture's simulated model output (or a deterministic mock agent).
    live: ask the Strands agent on Bedrock. Either way the policy validates before anything is returned."""
    return run_decision(req, get_settings())


@router.post("/api/evaluate")
@router.get("/api/report")
def evaluate():
    from ..evaluation import run_evaluation
    return run_evaluation()


@router.get("/api/cases/{case_id}")
def one_case(case_id: str):
    c = case_repo.get_case(case_id)
    if not c:
        raise HTTPException(404, "case not found")
    return c
