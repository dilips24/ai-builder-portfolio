---
id: RB-010
title: Voicemail Deposit and Retrieval Failures
doc_type: runbook
service: Voicemail
severity: SEV3
owner_team: Value Added Services
last_updated: 2026-03-03
---

# RB-010: Voicemail Deposit and Retrieval Failures

## Symptoms
- Callers hear silence or a fast busy tone instead of the greeting after the call is forwarded.
- Mailbox deposit failure rate rises above **1.5%** over 15 minutes.
- Storage volume `vm-store-01` is more than **85%** full.
- Subscribers dialling the retrieval number 1571 get "service not available".
- The visual-voicemail notification (MWI) does not light up although messages exist.

## Impact
Callers cannot leave messages and subscribers lose missed-call context. Because voicemail is a forwarding target for unanswered calls, a full failure also produces extra call-setup attempts on the core network.

## Diagnosis steps
1. Check storage: `vmctl store usage`. Anything above 85% triggers the housekeeping checks below.
2. Check the application servers: `vmctl node status`. Confirm all four nodes are `IN_SERVICE`.
3. Check forwarding conditions in the call-control platform for a recent configuration change; a wrong forward-on-busy destination yields silence.
4. For retrieval failures only, check the authentication service used by the PIN prompt: `vmctl auth probe`.
5. For a missing MWI, check the SMS-based notification queue (see RB-003).

## Resolution steps
1. Free storage: `vmctl purge --expired-greetings --older-than 90d`, then `vmctl purge --deleted-messages --older-than 7d`. This typically recovers 8–12% of volume.
2. If a node is out of service, restart it: `vmctl node restart --name <NODE>`; do not restart more than one node at a time.
3. If forwarding configuration is wrong, roll back the change using the change record and ask Core Signalling to verify.
4. Raise a capacity request when storage stays above 80% after housekeeping.

## Escalation
- VAS on-call is paged during business hours only; out of hours the Duty Manager decides.
- Escalate to VAS L2 if deposit failures remain above 1.5% **20 minutes** after the first action.
- Escalate to the vendor at **90 minutes**.

## Related docs
- RB-003 (SMS notifications for message-waiting indicators)
- RB-001 (call-forward data held in HLR)
