import unittest
from datetime import datetime

from agent import parse_decision, parse_facts
from fixtures import CASES, NOW, appt
from safeguard import ProposedDecision, apply_guard, check_decision


def verdict(case, decision=None):
    facts = parse_facts(CASES[case]["facts"])
    d = parse_decision(decision or CASES[case]["bad"])
    return facts, d, check_decision(facts, d)


class OriginalBadDecisionsAreCaught(unittest.TestCase):
    EXPECTED_RULE = {"A": "conflict", "B": "deferral", "C": "slot", "D": "status"}

    def test_every_original_decision_is_rejected_with_a_passing_alternative(self):
        for case, rule in self.EXPECTED_RULE.items():
            with self.subTest(case=case):
                facts, _, r = verdict(case)
                print(f"\n[Case {case}] rule={r.rule} | {r.reason}\n   safer: {r.safer_alternative.message}")
                self.assertFalse(r.acceptable)
                self.assertEqual(r.rule, rule)
                self.assertTrue(check_decision(facts, r.safer_alternative).acceptable)

    def test_case_a_alternative_confirms_and_does_not_escalate(self):
        self.assertEqual(verdict("A")[2].safer_alternative.action, "reply")

    def test_case_b_alternative_waits(self):
        self.assertEqual(verdict("B")[2].safer_alternative.action, "wait")

    def test_case_d_alternative_states_tentative_and_escalates(self):
        alt = verdict("D")[2].safer_alternative
        self.assertEqual(alt.action, "escalate")
        self.assertIn("tentative", alt.message)


class ValidDecisionsAreAccepted(unittest.TestCase):
    def ok(self, case, decision):
        r = verdict(case, decision)[2]
        self.assertTrue(r.acceptable, r.reason)

    def test_a_confirm_without_conflict(self):
        self.ok("A", {"action": "reply", "message": "Yes — your installation is confirmed for tomorrow, 09:00–12:00."})

    def test_b_acknowledge_and_wait(self):
        self.ok("B", {"action": "wait", "message": "No problem — message us when you're back."})

    def test_c_offer_real_slots(self):
        self.ok("C", {"action": "reply", "message": "Sorry, Saturday isn't available. We can come Monday 19 Oct "
                      "at 10:00 or Tuesday 20 Oct at 14:00 — which suits you?"})

    def test_c_book_available_slot_structured(self):
        self.ok("C", {"action": "reply", "message": "Booked for Monday at 10:00.",
                      "committed_slot_start": "2026-10-19T10:00:00"})

    def test_d_honest_tentative_status(self):
        self.ok("D", {"action": "escalate", "message": "Your appointment tomorrow is tentative and the crew "
                      "hasn't been confirmed yet. I'll let you know as soon as it is."})


class EdgeCases(unittest.TestCase):
    def test_case_c_structured_commit_to_unavailable_slot(self):
        r = verdict("C", {"action": "reply", "message": "You're all set.",
                          "committed_slot_start": "2026-10-17T10:00:00"})[2]
        self.assertFalse(r.acceptable)
        self.assertIn("not an available slot", r.reason)

    def test_case_c_no_slots_escalates(self):
        p = {**CASES["C"]["facts"], "available_slots": []}
        facts = parse_facts(p)
        r = check_decision(facts, ProposedDecision("reply", "Sure, see you Saturday!"))
        self.assertEqual(r.safer_alternative.action, "escalate")

    def test_case_c_negated_mention_is_not_a_commitment(self):
        self.assertTrue(verdict("C", {"action": "reply", "message": "Unfortunately we can't come on Saturday."})[2].acceptable)

    def test_case_a_real_overlap_with_active_job_is_a_valid_conflict(self):
        p = {**CASES["A"]["facts"], "other_jobs": [{"start": "2026-10-15T10:00:00", "end": "2026-10-15T13:00:00",
                                                    "crew": "crew-1", "status": "in_progress"}]}
        r = check_decision(parse_facts(p), parse_decision(CASES["A"]["bad"]))
        self.assertTrue(r.acceptable, r.reason)

    def test_case_a_active_but_non_overlapping_job_is_not_a_conflict(self):
        p = {**CASES["A"]["facts"], "other_jobs": [{"start": "2026-10-15T13:00:00", "end": "2026-10-15T15:00:00",
                                                    "crew": "crew-1", "status": "scheduled"}]}
        self.assertFalse(check_decision(parse_facts(p), parse_decision(CASES["A"]["bad"])).acceptable)

    def test_case_d_confirmed_crew_may_be_promised(self):
        p = {**CASES["D"]["facts"], "appointment": appt("confirmed", True)}
        self.assertTrue(check_decision(parse_facts(p), parse_decision(CASES["D"]["bad"])).acceptable)

    def test_case_d_confirmed_appointment_unknown_crew_cannot_promise_crew(self):
        p = {**CASES["D"]["facts"], "appointment": appt("confirmed", None)}
        self.assertFalse(check_decision(parse_facts(p), parse_decision(CASES["D"]["bad"])).acceptable)

    def test_case_b_wait_with_booking_push_is_rejected(self):
        r = verdict("B", {"action": "wait", "message": "Would you like to schedule something now?"})[2]
        self.assertFalse(r.acceptable)

    def test_apply_guard_returns_safe_decision(self):
        facts, d, _ = verdict("C")
        final, r = apply_guard(facts, d)
        self.assertFalse(r.acceptable)
        self.assertNotIn("Yes, we can come", final.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
