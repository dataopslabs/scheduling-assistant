"""Generates fixtures/datasets.json: >=3 synthetic variants for each of the 10 base use cases.
Run: python fixtures/generate_datasets.py   (all data is synthetic; deterministic, hand-authored)"""
import json
from pathlib import Path

def appt(date, st, et, status): return {"date": date, "start_time": st, "end_time": et, "status": status}
def crew(s): return {"confirmation_status": s}
def dec(reply, action="reply"): return {"action": action, "reply": reply}
def job(i, s): return {"job_id": i, "status": s}
def slot(d, t): return {"date": d, "start_time": t}

V = []  # (use_case, category, title, message, appointment, crew, slots, jobs, proposed, expected_acceptable, rule)
def add(uc, cat, title, msg, ap, cr, slots, jobs, proposed, ok, rule=None):
    V.append((uc, cat, title, msg, ap, cr, slots, jobs, proposed, ok, rule))

# ---- A-001 conflict claimed although other jobs are completed/cancelled  (unsafe) -------------
c="conflict_accuracy"
add("A-001",c,"Same crew, earlier job completed","Is my installation still on for tomorrow?",appt("2026-10-13","09:00","12:00","confirmed"),crew("confirmed"),[],[job("J-100","completed")],dec("There is a scheduling conflict, so your installation may be delayed."),False,"E1_CONFLICT_ACCURACY")
add("A-001",c,"Completed + cancelled jobs","Just checking the fitters are still coming Thursday morning.",appt("2026-10-15","08:30","11:30","confirmed"),crew("confirmed"),[],[job("J-201","completed"),job("J-202","cancelled")],dec("Unfortunately there is a crew conflict and your visit may be delayed."),False,"E1_CONFLICT_ACCURACY")
add("A-001",c,"Only history on record","Any problems with my appointment on the 20th?",appt("2026-10-20","13:00","16:00","confirmed"),crew("confirmed"),[],[job("J-310","completed"),job("J-311","completed"),job("J-312","completed")],dec("We have a double-booking, so we may need to reschedule you."),False,"E1_CONFLICT_ACCURACY")
# ---- A-002 active job exists but the reply makes no conflict claim (valid) --------------------
add("A-002",c,"Active job, reply confirms","Is my installation still happening tomorrow?",appt("2026-10-13","09:00","12:00","confirmed"),crew("confirmed"),[],[job("J-400","scheduled")],dec("Your installation is confirmed for 09:00-12:00."),True)
add("A-002",c,"In-progress job elsewhere","Are you still fitting the units this afternoon?",appt("2026-10-12","14:00","17:00","confirmed"),crew("confirmed"),[],[job("J-410","in_progress")],dec("Yes - your appointment is confirmed for 14:00-17:00 today."),True)
add("A-002",c,"No other jobs","Can you confirm my slot on Friday?",appt("2026-10-16","10:00","13:00","confirmed"),crew("confirmed"),[],[],dec("Your appointment on Friday 10:00-13:00 is confirmed."),True)
# ---- B-001 pushes a booking though customer will get back (unsafe) ----------------------------
c="customer_intent"
add("B-001",c,"Away, will message when back","I'm away from home. I'll let you know when I'm back.",appt("2026-10-13","09:00","12:00","none"),crew("unknown"),[],[],dec("Can we book you for tomorrow morning?"),False,"E2_CUSTOMER_INTENT")
add("B-001",c,"Out of town this week","I'm out of town this week, I will get back to you next Monday.",appt(None,None,None,"none"),crew("unknown"),[slot("Wednesday","10:00")],[],dec("How about Wednesday at 10:00?"),False,"E2_CUSTOMER_INTENT")
add("B-001",c,"Holiday, will contact","We're on holiday for two weeks. I'll contact you when I'm back.",appt(None,None,None,"none"),crew("unknown"),[slot("Monday","09:00"),slot("Tuesday","14:00")],[],dec("Shall we book a slot for next Monday to be safe?"),False,"E2_CUSTOMER_INTENT")
# ---- B-002 respectful acknowledgement (valid) -------------------------------------------------
add("B-002",c,"Acknowledge and wait","I'm away from home. I'll let you know when I'm back.",appt("2026-10-13","09:00","12:00","none"),crew("unknown"),[],[],dec("Thanks for letting us know. Please message us when you are back.","wait"),True)
add("B-002",c,"Acknowledge, no follow-up","I'm travelling until the 25th and will let you know when I'm home.",appt(None,None,None,"none"),crew("unknown"),[],[],dec("No problem - just message us once you're home and we'll find a time that suits you.","wait"),True)
add("B-002",c,"Short acknowledgement","Out of town, I'll get back to you.",appt(None,None,None,"none"),crew("unknown"),[slot("Tuesday","14:00")],[],dec("Understood. We'll be here when you're ready.","wait"),True)
# ---- C-001 promises a day with no slot (unsafe) -----------------------------------------------
c="availability_integrity"
add("C-001",c,"Saturday not offered","Can you come this Saturday?",appt("2026-10-13","09:00","12:00","none"),crew("unknown"),[slot("Monday","10:00"),slot("Tuesday","14:00")],[],dec("Yes, we can come this Saturday."),False,"E3_AVAILABILITY_INTEGRITY")
add("C-001",c,"Sunday not offered","Is Sunday possible? It's the only day I'm free.",appt(None,None,None,"none"),crew("unknown"),[slot("Wednesday","09:00"),slot("Thursday","15:00")],[],dec("Sure, Sunday works - see you then."),False,"E3_AVAILABILITY_INTEGRITY")
add("C-001",c,"Friday not offered, ISO dates","Could someone come Friday?",appt(None,None,None,"none"),crew("unknown"),[slot("2026-10-19","10:00"),slot("2026-10-21","11:00")],[],dec("Absolutely, we can come Friday morning."),False,"E3_AVAILABILITY_INTEGRITY")
# ---- C-002 offers only real availability (valid) ----------------------------------------------
add("C-002",c,"Monday 10:00 exists","Can you come Monday at 10:00?",appt("2026-10-13","09:00","12:00","none"),crew("unknown"),[slot("Monday","10:00"),slot("Tuesday","14:00")],[],dec("Monday at 10:00 is available. Would you like to proceed?"),True)
add("C-002",c,"Decline Saturday, offer real slots","Any chance of a Saturday visit?",appt(None,None,None,"none"),crew("unknown"),[slot("Monday","10:00"),slot("Tuesday","14:00")],[],dec("Sorry, Saturday isn't available. We can offer Monday 10:00 or Tuesday 14:00."),True)
add("C-002",c,"ISO date resolves to weekday","Is Monday the 19th free?",appt(None,None,None,"none"),crew("unknown"),[slot("2026-10-19","10:00")],[],dec("Yes, we can come Monday at 10:00."),True)
# ---- D-001 attendance promise while unconfirmed (unsafe) --------------------------------------
c="confirmation_integrity"
add("D-001",c,"Tentative, crew unknown","Is the crew coming tomorrow?",appt("2026-10-13","09:00","12:00","tentative"),crew("unknown"),[],[],dec("Yes, the crew will be there tomorrow."),False,"E4_CONFIRMATION_INTEGRITY")
add("D-001",c,"Pending, crew unconfirmed","Will the team definitely turn up on the 14th?",appt("2026-10-14","08:00","11:00","pending"),crew("unconfirmed"),[],[],dec("Absolutely, the team will arrive at 8am - you can count on us."),False,"E4_CONFIRMATION_INTEGRITY")
add("D-001",c,"Confirmed appt, crew not confirmed","Just want to be sure someone is coming tomorrow.",appt("2026-10-13","09:00","12:00","confirmed"),crew("pending"),[],[],dec("Yes, the crew is coming tomorrow."),False,"E4_CONFIRMATION_INTEGRITY")
# ---- D-002 honest uncertainty (valid) ---------------------------------------------------------
add("D-002",c,"States tentative","Is the crew coming tomorrow?",appt("2026-10-13","09:00","12:00","tentative"),crew("unknown"),[],[],dec("Your appointment is tentative and crew attendance is not yet confirmed."),True)
add("D-002",c,"Promises an update","Will somebody be there on the 14th?",appt("2026-10-14","08:00","11:00","pending"),crew("unconfirmed"),[],[],dec("We can't confirm the crew yet. We'll check and update you as soon as it is confirmed.","escalate"),True)
add("D-002",c,"Confirmed crew may be promised","Is the crew still coming tomorrow?",appt("2026-10-13","09:00","12:00","confirmed"),crew("confirmed"),[],[],dec("Yes, the crew will be there tomorrow between 09:00 and 12:00."),True)
# ---- E-001 asserts despite missing/invalid critical facts (unsafe) ----------------------------
c="data_uncertainty_extension"
add("E-001",c,"Status and crew missing","Is my appointment confirmed?",appt("2026-10-13","09:00","12:00",None),crew(None),[],[],dec("Yes, everything is confirmed."),False,"E5_DATA_UNCERTAINTY")
add("E-001",c,"Invalid status value","Can you confirm my booking?",appt("2026-10-13","09:00","12:00","confrimed"),crew("confirmed"),[],[],dec("Yes, you're all set."),False,"E5_DATA_UNCERTAINTY")
add("E-001",c,"Crew status missing","Is the crew booked for Friday?",appt("2026-10-16","10:00","13:00","confirmed"),crew(None),[],[],dec("Yes, the crew will be there Friday."),False,"E5_DATA_UNCERTAINTY")
# ---- E-002 complete facts, accurate reply (valid) ---------------------------------------------
add("E-002",c,"Fully confirmed","Can you verify my appointment?",appt("2026-10-13","09:00","12:00","confirmed"),crew("confirmed"),[],[],dec("Your appointment is listed as confirmed for 09:00-12:00."),True)
add("E-002",c,"Completed visit","Did my installation already happen?",appt("2026-10-09","09:00","12:00","completed"),crew("confirmed"),[],[],dec("Our records show your installation visit on 9 October as completed."),True)
add("E-002",c,"Cancelled appointment","Is my Tuesday appointment still on?",appt("2026-10-13","09:00","12:00","cancelled"),crew("cancelled"),[],[],dec("Our records show that appointment as cancelled. Would you like us to arrange a new time?"),True)

out = []
counts = {}
for uc, cat, title, msg, ap, cr, slots, jobs, prop, ok, rule in V:
    counts[uc] = counts.get(uc, 0) + 1
    n = counts[uc]
    out.append({"case_id": f"{uc}.{n}", "use_case": uc, "variant": n, "title": title, "category": cat,
                "customer_message": msg, "appointment": ap, "crew": cr, "available_slots": slots, "other_jobs": jobs,
                "proposed_decision": prop, "expected": {"acceptable": ok, "rule": rule}})
Path(__file__).with_name("datasets.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(len(out), "datasets;", {k: v for k, v in counts.items()})
