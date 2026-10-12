import json
import unittest

from fixtures import CASES
import agent
from handler import lambda_handler


class FakeBedrock:
    """Stands in for boto3 bedrock-runtime; records the request."""
    def __init__(self, text):
        self.text, self.calls = text, []

    def converse(self, **kw):
        self.calls.append(kw)
        return {"output": {"message": {"content": [{"text": self.text}]}}}


def event(body, method="POST", path="/decide"):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path, "body": json.dumps(body)}


class AgentTests(unittest.TestCase):
    def test_bad_model_output_is_guarded(self):
        fake = FakeBedrock('Sure! {"action":"reply","message":"Yes, we can come this Saturday.","committed_slot_start":null}')
        out = agent.run({"facts": CASES["C"]["facts"], "prompt": "naive"}, fake)
        print("\n[Agent/C naive] proposed:", out["proposed"]["message"], "\n   final:", out["final"]["message"])
        self.assertEqual(out["source"], "bedrock")
        self.assertFalse(out["guard"]["acceptable"])
        self.assertIn("Monday", out["final"]["message"])

    def test_good_model_output_passes_through(self):
        msg = "Sorry, Saturday isn't available. Monday 19 Oct at 10:00 or Tuesday 20 Oct at 14:00?"
        fake = FakeBedrock(json.dumps({"action": "reply", "message": msg, "committed_slot_start": None}))
        out = agent.run({"facts": CASES["C"]["facts"]}, fake)
        self.assertTrue(out["guard"]["acceptable"])
        self.assertEqual(out["final"]["message"], msg)

    def test_prompt_selection_and_system_prompt_sent(self):
        fake = FakeBedrock('{"action":"wait","message":"ok"}')
        agent.run({"facts": CASES["B"]["facts"], "prompt": "improved"}, fake)
        self.assertIn("ONLY the scheduling facts", fake.calls[0]["system"][0]["text"])
        self.assertEqual(fake.calls[0]["inferenceConfig"]["temperature"], 0)

    def test_unparseable_model_output_escalates(self):
        out = agent.run({"facts": CASES["C"]["facts"]}, FakeBedrock("I cannot help"))
        self.assertEqual(out["final"]["action"], "escalate")
        self.assertEqual(out["guard"]["rule"], "model_error")

    def test_simulated_decision_skips_bedrock(self):
        out = agent.run({"facts": CASES["D"]["facts"], "simulated_decision": CASES["D"]["bad"]}, client=None)
        self.assertEqual(out["source"], "simulated")
        self.assertEqual(out["guard"]["rule"], "status")

    def test_guard_can_be_disabled_to_show_the_raw_failure(self):
        out = agent.run({"facts": CASES["C"]["facts"], "simulated_decision": CASES["C"]["bad"], "guard": False})
        self.assertEqual(out["final"]["message"], CASES["C"]["bad"]["message"])
        self.assertFalse(out["guard"]["acceptable"])


class HandlerTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(lambda_handler(event({}, "GET", "/health"))["statusCode"], 200)

    def test_decide_ok(self):
        r = lambda_handler(event({"facts": CASES["A"]["facts"], "simulated_decision": CASES["A"]["bad"]}))
        self.assertEqual(r["statusCode"], 200)
        self.assertEqual(json.loads(r["body"])["guard"]["rule"], "conflict")

    def test_missing_facts_is_400(self):
        self.assertEqual(lambda_handler(event({}))["statusCode"], 400)

    def test_bad_json_is_400(self):
        e = event({}); e["body"] = "{nope"
        self.assertEqual(lambda_handler(e)["statusCode"], 400)

    def test_unknown_route_is_404(self):
        self.assertEqual(lambda_handler(event({}, "GET", "/x"))["statusCode"], 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
