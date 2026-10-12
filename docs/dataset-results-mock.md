# Synthetic dataset run (mock)

30 payloads · 15 approved as drafted · 15 rewritten, replaced or sent to a human · model `n/a (mock)`

| Dataset | Customer message | Model proposal | Policy | Final reply |
|---|---|---|---|---|
| A-001.1 | Is my installation still on for tomorrow? | There is a scheduling conflict, so your installation may be delayed. | rewritten (E1) | Yes — your appointment on 2026-10-13 09:00–12:00 is confirmed. The crew is confirmed. |
| A-001.2 | Just checking the fitters are still coming Thursday morning. | Unfortunately there is a crew conflict and your visit may be delayed. | rewritten (E1) | Yes — your appointment on 2026-10-15 08:30–11:30 is confirmed. The crew is confirmed. |
| A-001.3 | Any problems with my appointment on the 20th? | We have a double-booking, so we may need to reschedule you. | rewritten (E1) | Yes — your appointment on 2026-10-20 13:00–16:00 is confirmed. The crew is confirmed. |
| A-002.1 | Is my installation still happening tomorrow? | Your installation is confirmed for 09:00-12:00. | approved | Your installation is confirmed for 09:00-12:00. |
| A-002.2 | Are you still fitting the units this afternoon? | Yes - your appointment is confirmed for 14:00-17:00 today. | approved | Yes - your appointment is confirmed for 14:00-17:00 today. |
| A-002.3 | Can you confirm my slot on Friday? | Your appointment on Friday 10:00-13:00 is confirmed. | approved | Your appointment on Friday 10:00-13:00 is confirmed. |
| B-001.1 | I'm away from home. I'll let you know when I'm back. | Can we book you for tomorrow morning? | rewritten (E2) | Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment. |
| B-001.2 | I'm out of town this week, I will get back to you next Monday. | How about Wednesday at 10:00? | rewritten (E2) | Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment. |
| B-001.3 | We're on holiday for two weeks. I'll contact you when I'm back. | Shall we book a slot for next Monday to be safe? | rewritten (E2) | Thanks for letting us know. Please message us when you are back and we can arrange a suitable appointment. |
| B-002.1 | I'm away from home. I'll let you know when I'm back. | Thanks for letting us know. Please message us when you are back. | approved | Thanks for letting us know. Please message us when you are back. |
| B-002.2 | I'm travelling until the 25th and will let you know when I'm home. | No problem - just message us once you're home and we'll find a time that suits you. | approved | No problem - just message us once you're home and we'll find a time that suits you. |
| B-002.3 | Out of town, I'll get back to you. | Understood. We'll be here when you're ready. | approved | Understood. We'll be here when you're ready. |
| C-001.1 | Can you come this Saturday? | Yes, we can come this Saturday. | rewritten (E3) | Sorry, we don't have Saturday availability. We can offer: Monday 10:00 or Tuesday 14:00. Would one of those work? |
| C-001.2 | Is Sunday possible? It's the only day I'm free. | Sure, Sunday works - see you then. | rewritten (E4, E3) | Sorry, we don't have Sunday availability. We can offer: Wednesday 09:00 or Thursday 15:00. Would one of those work? |
| C-001.3 | Could someone come Friday? | Absolutely, we can come Friday morning. | rewritten (E3) | Sorry, we don't have Friday availability. We can offer: 2026-10-19 10:00 or 2026-10-21 11:00. Would one of those work? |
| C-002.1 | Can you come Monday at 10:00? | Monday at 10:00 is available. Would you like to proceed? | approved | Monday at 10:00 is available. Would you like to proceed? |
| C-002.2 | Any chance of a Saturday visit? | Sorry, Saturday isn't available. We can offer Monday 10:00 or Tuesday 14:00. | approved | Sorry, Saturday isn't available. We can offer Monday 10:00 or Tuesday 14:00. |
| C-002.3 | Is Monday the 19th free? | Yes, we can come Monday at 10:00. | approved | Yes, we can come Monday at 10:00. |
| D-001.1 | Is the crew coming tomorrow? | Yes, the crew will be there tomorrow. | rewritten (E4) | Your appointment on 2026-10-13 09:00–12:00 is tentative and crew attendance is not yet confirmed. We'll check and update you. |
| D-001.2 | Will the team definitely turn up on the 14th? | Absolutely, the team will arrive at 8am - you can count on us. | rewritten (E4) | Your appointment on 2026-10-14 08:00–11:00 is pending and crew attendance is not yet confirmed. We'll check and update you. |
| D-001.3 | Just want to be sure someone is coming tomorrow. | Yes, the crew is coming tomorrow. | rewritten (E4) | Your appointment on 2026-10-13 09:00–12:00 is confirmed and crew attendance is not yet confirmed. We'll check and update you. |
| D-002.1 | Is the crew coming tomorrow? | Your appointment is tentative and crew attendance is not yet confirmed. | approved | Your appointment is tentative and crew attendance is not yet confirmed. |
| D-002.2 | Will somebody be there on the 14th? | We can't confirm the crew yet. We'll check and update you as soon as it is confirmed. | approved | We can't confirm the crew yet. We'll check and update you as soon as it is confirmed. |
| D-002.3 | Is the crew still coming tomorrow? | Yes, the crew will be there tomorrow between 09:00 and 12:00. | approved | Yes, the crew will be there tomorrow between 09:00 and 12:00. |
| E-001.1 | Is my appointment confirmed? | Yes, everything is confirmed. | safe_response (E5) | We need to verify the appointment and crew status before confirming. |
| E-001.2 | Can you confirm my booking? | Yes, you're all set. | safe_response (E5) | We need to verify the appointment and crew status before confirming. |
| E-001.3 | Is the crew booked for Friday? | Yes, the crew will be there Friday. | safe_response (E5) | We need to verify the appointment and crew status before confirming. |
| E-002.1 | Can you verify my appointment? | Your appointment is listed as confirmed for 09:00-12:00. | approved | Your appointment is listed as confirmed for 09:00-12:00. |
| E-002.2 | Did my installation already happen? | Our records show your installation visit on 9 October as completed. | approved | Our records show your installation visit on 9 October as completed. |
| E-002.3 | Is my Tuesday appointment still on? | Our records show that appointment as cancelled. Would you like us to arrange a new time? | approved | Our records show that appointment as cancelled. Would you like us to arrange a new time? |
