---
id: RB-003
title: SMS Gateway Message Queue Backlog and Delivery Degradation
doc_type: runbook
service: SMS Gateway
severity: SEV2
owner_team: Messaging Platform
last_updated: 2026-04-02
---

# RB-003: SMS Gateway Message Queue Backlog and Delivery Degradation

## Symptoms
- Outbound queue depth above **50,000 messages** for more than 5 minutes.
- Delivery-receipt success rate below **92%** over a rolling 10-minute window.
- One or more SMPP binds to an aggregator show `UNBOUND` or repeated `ESME_RTHROTTLED` responses.
- One-time-passcode messages arrive minutes late; marketing campaigns are still sending.

## Impact
Customers cannot complete login or payment verification that relies on a one-time passcode. Enterprise A2P customers see missed delivery SLAs. Voice and data are unaffected.

## Diagnosis steps
1. Run `smsgwctl queue stats` and read depth per traffic class (OTP, transactional, campaign).
2. Run `smsgwctl bind list`. Identify any bind in `UNBOUND` state and its aggregator.
3. Check whether a campaign started in the last 15 minutes in the campaign scheduler. Campaign traffic and OTP share the same outbound connections.
4. If throttle responses (`ESME_RTHROTTLED`) dominate, the aggregator is limiting you; check the current outbound rate with `smsgwctl rate show`.

## Resolution steps
1. If a campaign is saturating capacity: suspend it with `smsgwctl campaign pause --id <ID>` and cap campaign traffic at **400 messages per second** using `smsgwctl rate set --class campaign --mps 400`.
2. For an unbound aggregator link: `smsgwctl bind restart --name <BIND>`. If it does not rebind within 3 minutes, route to the secondary aggregator with `smsgwctl route failover --to agg-secondary`.
3. Always keep OTP traffic at highest priority: confirm with `smsgwctl priority show` that class OTP has priority 1.
4. Once queue depth is under 5,000, resume the campaign gradually in steps of 100 messages per second.

## Escalation
- Messaging Platform on-call is paged automatically at the queue threshold.
- Escalate to Messaging Platform L2 if OTP delivery is still degraded **10 minutes** after the first page.
- Escalate to the aggregator account manager and the Duty Manager at **25 minutes**.

## Related docs
- PM-004 (an expired certificate also blocked SMS traffic)
- RB-006 (API gateway errors for the OTP request API)
