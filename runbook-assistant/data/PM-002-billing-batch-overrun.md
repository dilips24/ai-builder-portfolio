---
id: PM-002
title: Postmortem - Billing Batch Overran Into Business Hours
doc_type: postmortem
service: Billing Batch
severity: SEV2
owner_team: Revenue Assurance
last_updated: 2026-03-05
---

# PM-002: Billing Batch Overran Into Business Hours

## Summary
On 26 February 2026 the nightly rating batch finished at 09:48 instead of before 05:30. The bill run for 1.9 million postpaid accounts was postponed by one day and some customers received balance notifications with wrong amounts. No money was lost, but 214 customer complaints were logged.

## Timeline
- 01:10 Batch `nightly-rate` starts normally.
- 02:30 A Revenue Assurance analyst starts an ad-hoc margin report on the production rating schema.
- 03:00 Progress is at 41%; the page goes out. On-call sees throughput at 70,000 records per minute.
- 03:20 On-call suspects a bad tariff table and spends 40 minutes reviewing the reject counter, which is normal.
- 04:05 Lock check shows the report session holding a table lock; the session is terminated.
- 04:15 Throughput returns to 140,000 records per minute.
- 04:35 Escalated to Billing Ops L3 after the 30-minute rule had already been exceeded.
- 09:48 Batch completes.

## Root cause
A long-running read-write ad-hoc report took a lock on the rating schema and slowed the batch. The report ran on production because the reporting replica was being rebuilt that week and the analyst was given production access as a stop-gap. The runbook mentions lock contention but ranks it after reference-table problems, so the on-call checked the wrong cause first.

## What went well
- The 03:00 progress alarm triggered as designed.
- Resume from checkpoint worked and avoided a restart.

## What did not go well
- Diagnosis order delayed the fix by about 45 minutes.
- Finance was not told until 06:00.

## Action items
1. Block interactive sessions on the rating schema between 01:00 and 06:00 (owner: Database Services, due 2026-03-31).
2. Reorder the runbook so `billctl db locks` is run first when throughput is low and the reject counter is normal.
3. Lesson not in the runbook: when the batch will clearly miss 05:30, **notify Finance at 04:30 even if the cause is unknown**, and decide on a bill-run delay before 05:00, rather than waiting for the 60-minute escalation.
4. Restore the reporting replica and withdraw the stop-gap production access.

## Linked runbook
RB-002 (Nightly Billing Rating Batch Delayed or Stalled)
