"""Run every synthetic dataset through the agent and policy; write JSON + Markdown reports.

  python -m app.batch --mode mock            # replay the recorded model outputs
  python -m app.batch --mode live            # send each payload to the LLM (needs AWS creds + Bedrock access)
"""
import argparse
import json
from pathlib import Path
from .config import get_settings
from .schemas import DecideRequest, SchedulingCase
from .services import cases as repo
from .services.decision import decide

OUT = Path(__file__).resolve().parent.parent.parent / "docs"


def run(mode: str) -> list[dict]:
    rows = []
    for d in repo.list_datasets():
        case = SchedulingCase.model_validate(d)
        r = decide(DecideRequest(mode=mode, case=case), get_settings())
        rows.append({"case_id": case.case_id, "use_case": case.use_case, "title": case.title, "customer_message": case.customer_message,
                     "payload": r.evidence.facts, "expected": d["expected"], "source": r.evidence.source, "model_id": r.evidence.model_id,
                     "latency_ms": r.evidence.latency_ms, "proposed": r.proposed_decision.model_dump(), "approved": r.acceptable,
                     "rules": [f.rule_id for f in r.findings], "final": {"action": r.final_action, "reply": r.final_reply},
                     "error": r.evidence.error})
        print(f"{case.case_id:6} {r.evidence.source:16} {'OK ' if r.acceptable else 'BLK'} {r.evidence.latency_ms:5}ms  {r.proposed_decision.reply[:80]}")
    return rows


def markdown(rows: list[dict], mode: str) -> str:
    n = len(rows); ok = sum(r["approved"] for r in rows)
    lines = [f"# Synthetic dataset run ({mode})", "", f"{n} payloads · {ok} approved · {n - ok} blocked by policy · model `{rows[0]['model_id'] or 'n/a (mock)'}`", "",
             "| Dataset | Customer message | Model proposal | Policy | Final reply |", "|---|---|---|---|---|"]
    for r in rows:
        esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
        verdict = "approved" if r["approved"] else "blocked " + ", ".join(x.split("_")[0] for x in r["rules"])
        lines.append(f"| {r['case_id']} | {esc(r['customer_message'])} | {esc(r['proposed']['reply'])} | {verdict} | {esc(r['final']['reply'])} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", choices=["mock", "live"], default="mock")
    mode = ap.parse_args().mode
    rows = run(mode)
    OUT.mkdir(exist_ok=True)
    (OUT / f"dataset-results-{mode}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    (OUT / f"dataset-results-{mode}.md").write_text(markdown(rows, mode))
