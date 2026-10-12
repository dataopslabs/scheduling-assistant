"""Synthetic scenarios from the task. "Now" is Wednesday 14 Oct 2026 09:00."""
from datetime import datetime as dt

NOW = "2026-10-14T09:00:00"


def appt(status="confirmed", crew_confirmed=None):
    return {"start": "2026-10-15T09:00:00", "end": "2026-10-15T12:00:00", "status": status,
            "crew": "crew-1", "crew_confirmed": crew_confirmed}


CASES = {
    "A": {"facts": {"now": NOW, "customer_message": "Is my installation still happening tomorrow?",
                    "appointment": appt("confirmed"),
                    "other_jobs": [{"start": "2026-10-15T08:00:00", "end": "2026-10-15T10:00:00",
                                    "crew": "crew-1", "status": "completed"}]},
          "bad": {"action": "escalate", "message": "There is a scheduling conflict, so your installation may be delayed."}},
    "B": {"facts": {"now": NOW, "customer_message": "I'm away from home. I'll let you know when I'm back."},
          "bad": {"action": "reply", "message": "Can we book you for tomorrow morning?"}},
    "C": {"facts": {"now": NOW, "customer_message": "Can you come this Saturday?",
                    "available_slots": [{"start": "2026-10-19T10:00:00", "end": "2026-10-19T12:00:00"},
                                        {"start": "2026-10-20T14:00:00", "end": "2026-10-20T16:00:00"}]},
          "bad": {"action": "reply", "message": "Yes, we can come this Saturday."}},
    "D": {"facts": {"now": NOW, "customer_message": "Is the crew coming tomorrow?",
                    "appointment": appt("tentative", None)},
          "bad": {"action": "reply", "message": "Yes, the crew will be there tomorrow."}},
}
