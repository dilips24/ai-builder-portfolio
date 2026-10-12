---
id: RB-002
title: Nightly Billing Rating Batch Delayed or Stalled
doc_type: runbook
service: Billing Batch
severity: SEV2
owner_team: Revenue Assurance
last_updated: 2026-02-20
---

# RB-002: Nightly Billing Rating Batch Delayed or Stalled

## Symptoms
- The `nightly-rate` run has not reached **70% completion by 03:00**.
- Records processed per minute fall below 120,000 for 15 minutes with no error in the job log.
- The downstream invoice generation job is still in `WAITING` state at 05:00.
- Customer-care agents see usage totals that are a day old.


## Impact
Invoices and balance notifications are late. If the rating batch does not finish by **05:30**, the bill-run window for the morning is missed and prepaid balance corrections are delayed by a full day. No direct network impact. Customer will be allowed to make calls even thier balance is negaive,

## Diagnosis steps
1. Check job state: `billctl batch status --run nightly-rate`. Note the current stage (MEDIATION_IN, RATING, AGGREGATION).
2. If the stage is RATING and throughput is low, look at the rejected-record counter: `billctl batch rejects --run nightly-rate`. More than 40,000 rejects usually means a bad tariff reference table load.
3. Check database locks on the rating schema: `billctl db locks`. Long-held locks from an ad-hoc report are a common cause.
4. Confirm that the mediation file drop completed; a late CDR file from the roaming clearing partner can leave the batch waiting.

## Resolution steps
1. For lock contention: kill the blocking session identified by `billctl db locks`, then confirm throughput recovers within 5 minutes.
2. For a bad reference table: roll back the tariff table with `billctl ref rollback --table tariff --to previous`, then resume.
3. To restart without reprocessing completed work: `billctl batch resume --run nightly-rate --from-checkpoint`. Never use `--restart` after 03:00, because a full restart cannot finish before 05:30.
4. If a mediation file is missing, request a resend from Revenue Assurance and let the batch continue with `--skip-missing-file` only with Duty Manager approval.

## Escalation
- Revenue Assurance on-call is paged at 03:00 if progress is under 70%.
- Escalate to Billing Ops L3 if the batch is not progressing **30 minutes** after the first page.
- Notify the Finance Operations lead at **60 minutes**, or at 04:30 whichever comes first, that the bill run is at risk.

## Related docs
- PM-002 (billing batch overrun postmortem)
- RB-009 (late roaming CDR files)
