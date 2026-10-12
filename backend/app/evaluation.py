import json
from pathlib import Path
from .schemas import SchedulingCase
from .policy import validate
DATA=Path(__file__).resolve().parent.parent/"data"/"cases.json"
def run_evaluation():
    fixtures=json.loads(DATA.read_text())
    results=[]; unsafe=unsafe_accepted=valid=valid_rejected=0
    for raw in fixtures:
        case=SchedulingCase.model_validate(raw); findings=validate(case,case.proposed_decision)
        actual=not findings; expected=raw["expected"]["acceptable"]; passed=actual==expected
        if not expected: unsafe+=1; unsafe_accepted+=int(actual)
        else: valid+=1; valid_rejected+=int(not actual)
        results.append({"case_id":case.case_id,"category":case.category,"expected_acceptable":expected,
          "actual_acceptable":actual,"passed":passed,"rules":[f.rule_id for f in findings],
          "reason":findings[0].reason if findings else "No implemented policy violation detected."})
    total=len(results); passed=sum(x["passed"] for x in results)
    return {"total":total,"passed":passed,"pass_rate":round(passed/total,4) if total else 0,
      "unsafe_acceptance_rate":round(unsafe_accepted/unsafe,4) if unsafe else 0,
      "valid_decision_rejection_rate":round(valid_rejected/valid,4) if valid else 0,
      "results":results,"interpretation":"Synthetic fixture metrics only; not a live-LLM quality score."}
if __name__=="__main__":
    print(json.dumps(run_evaluation(),indent=2))
