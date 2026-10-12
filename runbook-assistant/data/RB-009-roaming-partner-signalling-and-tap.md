---
id: RB-009
title: Roaming Partner Signalling Failures and Late TAP Files
doc_type: runbook
service: Roaming
severity: SEV3
owner_team: Roaming Partnerships
last_updated: 2026-01-12
---

# RB-009: Roaming Partner Signalling Failures and Late TAP Files

## Symptoms
- Outbound roamers (our subscribers abroad) report no data on one specific visited network, while others work.
- Inbound roaming attach success from a partner PLMN falls below 85% over 30 minutes.
- The steering-of-roaming platform logs repeated `SOR_TIMEOUT` events for a single partner.
- TAP files from a partner have not arrived within **36 hours** of the usage period close.

## Impact
Subscribers abroad cannot use data or make calls on the affected network, and may be unable to use the automatic fallback. Late TAP files delay wholesale billing and inflate month-end accruals. Inbound partner customers may complain to their own operator about us.

## Diagnosis steps
1. Check partner status: `roamctl partner status --plmn 99901` (replace with the partner PLMN code). Look at the signalling link state and the last 24 hours of attach success.
2. Confirm the problem is not on our side by testing another partner on the same signalling route: `roamctl link test --route sigtran-east`.
3. Check the roaming agreement record for the partner: a recently expired IR.21 (network information document) or changed GT range can break attach silently.
4. For late TAP, check the clearing house inbox: `roamctl tap list --partner <PLMN> --period <YYYY-MM>`.

## Resolution steps
1. If the link is down on our side, restart the SS7 association: `roamctl link restart --route sigtran-east`.
2. If the partner changed its Global Title range, load the new range with `roamctl partner update --plmn <PLMN> --gt-file <FILE>`.
3. Turn off steering to the failing partner so subscribers can fall back to the second preferred network: `roamctl sor exclude --plmn <PLMN> --hours 12`.
4. For late TAP, request a resend through the clearing house; log a dispute if the file is more than **5 days** late.

## Escalation
- Roaming Partnerships on-call handles alarms during business hours and by phone out of hours.
- Escalate to the partner's NOC contact if no fix **30 minutes** after confirming the fault is theirs.
- Escalate to the Head of Wholesale and the Duty Manager at **2 hours** for a top-10 destination country.

## Related docs
- RB-001 (HLR/HSS authentication failures)
- RB-002 (CDR files for billing)
