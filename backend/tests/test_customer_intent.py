"""E2: if the customer will get back to us, do not push a booking."""
from helpers import case, rules

AWAY = "I'm away from home. I'll let you know when I'm back."


def kw(reply): return case(AWAY, reply, status="none", crew="unknown")


def test_booking_push_is_blocked():
    for reply in ("Can we book you for tomorrow morning?", "How about Friday?", "Shall we book a slot?", "Would you like to schedule now?"):
        assert rules(kw(reply)) == ["E2_CUSTOMER_INTENT"], reply


def test_acknowledgement_is_accepted():
    assert rules(kw("Thanks for letting us know. Please message us when you are back.")) == []


def test_neutral_scheduling_word_is_not_a_push():
    assert rules(kw("Understood, message us when you're back so we can schedule your appointment.")) == []


def test_pushing_is_fine_when_customer_did_not_defer():
    assert rules(case("Can you come Monday?", "Would you like to proceed?", status="none", crew="unknown")) == []
