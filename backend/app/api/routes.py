from fastapi import APIRouter, HTTPException
from ..config import get_settings
from ..schemas import BatchRequest, BatchResponse, DecideRequest, DecisionResponse
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


@router.get("/api/datasets")
def datasets(use_case: str | None = None):
    """Synthetic dataset variants (>=3 per use case). Optional filter ?use_case=A-001."""
    return case_repo.list_datasets(use_case)


@router.post("/api/batch", response_model=BatchResponse)
def batch(req: BatchRequest):
    """Run several datasets through the agent (mock or live) and the policy. Max 10 per call (Lambda/API Gateway time limit)."""
    from ..schemas import BatchItem, SchedulingCase
    pool = case_repo.list_datasets(req.use_case) if req.use_case else [d for d in case_repo.list_datasets() if req.case_ids and d["case_id"] in req.case_ids]
    if not pool:
        raise HTTPException(404, "no matching datasets")
    if len(pool) > 10:
        raise HTTPException(422, "batch limited to 10 datasets per request")
    items = []
    for d in pool:
        case = SchedulingCase.model_validate(d)
        items.append(BatchItem(case_id=case.case_id, title=case.title, customer_message=case.customer_message,
                               expected_acceptable=(d.get("expected") or {}).get("acceptable"),
                               decision=run_decision(DecideRequest(mode=req.mode, case=case), get_settings())))
    ok = sum(i.decision.acceptable for i in items)
    return BatchResponse(mode=req.mode, total=len(items), approved=ok, blocked=len(items) - ok, items=items)
