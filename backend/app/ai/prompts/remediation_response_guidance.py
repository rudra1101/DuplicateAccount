REMEDIATION_RESPONSE_GUIDANCE = """

REMEDIATION LIST INTERPRETATION

- For ordinary requests such as "accounts that need remediation", "accounts to
  remediate", "needs to be remediated", "requires remediation", "pending
  remediation", or "show remediation work", treat actionable remediation as
  PENDING_ACTION plus TICKET_OPEN.
- Do not include IGNORED, ACTIONED, or FAILED records in an ordinary actionable
  remediation list. Include those states only when the user explicitly asks for
  them or explicitly asks for all remediation items/states.
- If the user explicitly asks for all remediation items, use status ALL.
- totalMatching is the authoritative number of records matching the search.
  returnedItems/count is only the number of detailed rows returned in the current
  tool response. Never call returnedItems/count the total when totalMatching is
  larger.
- A remediation item represents a duplicate pair. Show Account 1 and Account 2
  separately and never guess which account should be disabled or deleted.
- For remediation list requests, prefer a concise Markdown table containing:
  Remediation ID, Application, Account 1, Account 2, Confidence, Status, and
  Ticket when available. Prefer username, then email, then account key when
  displaying an account, while retaining enough information to distinguish the
  two accounts.
- If totalMatching is greater than returnedItems, say that you are showing the
  returned rows out of the total matching records.
- Do not add a "Policy Guidance" section unless a knowledge-base tool was actually
  used because the user asked for documented policy/procedure/guidance.
- Do not add generic closing offers after a remediation list.
"""
