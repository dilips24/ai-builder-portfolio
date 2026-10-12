---
id: RB-007
title: Number Porting Requests Stuck Between Operators
doc_type: runbook
service: Number Porting
severity: SEV3
owner_team: Porting Ops
last_updated: 2026-02-05
---

# RB-007: Number Porting Requests Stuck Between Operators

## Symptoms
- Port-in requests remain in status `PENDING_DONOR` for longer than **4 business hours**.
- The porting clearing house returns `NACK` with reason code `P14` (validation mismatch) on more than 8% of submissions in a day.
- Customers report "I changed provider but my old number still rings on the old SIM" after the scheduled cut-over time.
- The nightly port-out reconciliation report shows numbers with two active owners.

## Impact
The regulator allows a maximum of **2 working days** for a standard port. Requests that miss the window create compliance breaches and customer complaints. Customers whose cut-over fails can lose inbound calls and SMS until the routing is corrected.

## Diagnosis steps
1. Look up the request: `portctl request show --id <REQUEST_ID>`. Record the status, the donor operator and the time of the last message exchanged.
2. Check clearing house connectivity: `portctl link status`. A link in `DEGRADED` explains many simultaneous stuck requests.
3. For `P14` rejections, compare the customer name, ID number and account number on the request against the CRM record. Most `P14` rejections are typos or a mismatched ID format.
4. For cut-over failures, check the routing record: `portctl route show --msisdn <MSISDN>`. If the routing still points at the donor, the cut-over message was not applied.

## Resolution steps
1. Resend a stuck request once: `portctl request resend --id <REQUEST_ID>`. Do not resend more than once; duplicates cause `P22` (duplicate request) rejections.
2. For `P14`, correct the data in CRM and resubmit with `portctl request amend --id <REQUEST_ID>`.
3. For failed cut-over, apply the routing manually: `portctl route apply --msisdn <MSISDN> --to northwind` and ask the Core Signalling team to confirm the HLR update.
4. Record every manual correction in the porting case log for the regulator audit.

## Escalation
- Porting Ops queue handles the first line during business hours (08:00–18:00).
- Escalate to the Porting Ops team lead if a request is still stuck after **60 minutes** of own handling.
- Escalate to the donor operator's porting desk, with the Duty Manager copied, at **4 hours**.

## Related docs
- RB-001 (HLR update after cut-over)
- RB-008 (SIM activation for new SIMs accompanying a port)
