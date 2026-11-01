from common import TIER_DESC
SETTING="A developer sends this request to an AI coding agent. Decide which model tier should handle it."
QUESTIONS={
 "tier":{"type":"choice","instructions":"Which is the cheapest model tier that would reliably complete this coding request correctly?","criteria":TIER_DESC},
 "urgent":{"type":"noul","instructions":"The user signals urgency or production impact (for example 'urgent', 'ASAP', production is down, an outage, customers are blocked)."},
 "ripple":{"type":"noul","instructions":"The requested change could ripple across the codebase (for example a major dependency or framework upgrade, or a wide migration touching many files)."},
}
def state(q): return {"setting":SETTING,"request":q}
def state_text(q): return f"setting: {SETTING}\nrequest: {q}"
def apply_rules(tier,urgent,ripple): return "frontier" if (urgent>0.5 or ripple>0.5) else tier
