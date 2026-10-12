import json
import unittest

from fixtures import CASES
import agent
from handler import lambda_handler


class FakeBedrock:
    """Stands in for a strands.Agent: callable, str(result) is the model text."""
    def __init__(self, text):
        self.text, self.prompts = text, []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.text


def event(body, method="POST", path="/decide"):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path, "body": json.dumps(body)}


class AgentTests(unittest.TestCase):
    def test_bad_model_output_is_guarded(self):
        fake = FakeBedrock('Sure! {"action":"reply","message":"Yes, we can come this Saturday.","committed_slot_start":null}')
        out = agent.run({"facts": CASES["C"]["facts"], "prompt": "naive"}, fake)
        print("\n[Agent/C naive] proposed:", out["proposed"]["message"], "\n   final:", out["final"]["message"])
        self.assertEqual(out["source"], "strands-bedrock")
        self.assertFalse(out["guard"]["acceptable"])
        self.assertIn("Monday", out["final"]["message"])

    def test_good_model_output_passes_through(self):
        msg = "Sorry, Saturday isn't available. Monday 19 Oct at 10:00 or Tuesday 20 Oct at 14:00?"
        fake = FakeBedrock(json.dumps({"action": "reply", "message": msg, "committed_slot_start": None}))
        out = agent.run({"facts": CASES["C"]["facts"]}, fake)
        self.assertTrue(out["guard"]["acceptable"])
        self.assertEqual(out["final"]["message"], msg)

    def test_prompt_files_and_agent_factory(self):
        self.assertIn("ONLY the scheduling facts", agent.load_prompt("improved"))
        self.assertIn("Be proactive", agent.load_prompt("naive"))
        fake = FakeBedrock('{"action":"wait","message":"ok"}')
        agent.run({"facts": CASES["B"]["facts"]}, fake)
        self.assertIn("Respond with JSON only", fake.prompts[0])

    def test_make_agent_builds_strands_agent_on_bedrock_model(self):
        a = agent.make_agent("sys", "some-model-id")
        self.assertEqual(a.model.config["model_id"], "some-model-id")
        self.assertEqual(a.system_prompt, "sys")

    def test_unparseable_model_output_escalates(self):
        out = agent.run({"facts": CASES["C"]["facts"]}, FakeBedrock("I cannot help"))
        self.assertEqual(out["final"]["action"], "escalate")
        self.assertEqual(out["guard"]["rule"], "model_error")

    def test_simulated_decision_skips_bedrock(self):
        out = agent.run({"facts": CASES["D"]["facts"], "simulated_decision": CASES["D"]["bad"]})
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
