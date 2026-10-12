---
id: PM-006
title: Postmortem - eSIM Activation Backlog on Launch Weekend
doc_type: postmortem
service: SIM Activation
severity: SEV2
owner_team: Provisioning
last_updated: 2026-05-22
---

# PM-006: eSIM Activation Backlog on Launch Weekend

## Summary
On Saturday 16 May 2026, the launch day of a new smartphone, the eSIM activation lane stalled for 58 minutes. About 3,100 customers completed the download of their eSIM profile but could not start service. Stores had queues of customers waiting at the counter.

## Timeline
- 09:02 Store opening; activations ramp to 4 times a normal Saturday.
- 09:41 One message fails repeatedly on a malformed device identifier and blocks the head of the `esim` lane.
- 09:49 The oldest-message alarm fires (8-minute limit); Provisioning is paged.
- 09:58 On-call suspects HSS capacity and checks RB-001 for twenty minutes, finding nothing wrong.
- 10:20 Another engineer peeks the lane and identifies the poison message.
- 10:24 Message quarantined; the lane starts moving.
- 10:39 Queue is clear after draining with concurrency 5.

## Root cause
Poison message at the head of a strictly ordered lane. The activation consumer retried the same message indefinitely instead of dead-lettering it after a limited number of attempts. The lane had been configured for strict ordering during a previous migration and not reverted.

## What went well
- Quarantine and replay in batches of 500 worked cleanly and no activations were lost.
- Stores received status messages from the retail operations team.

## What did not go well
- The on-call went to the HSS runbook first because the symptom page in RB-008 lists HSS as the first downstream dependency to check.
- No capacity planning for launch weekend was done.

## Action items
1. Set the maximum retries to 5 and dead-letter afterwards (owner: Provisioning, due 2026-06-12).
2. Remove strict ordering from the `esim` lane.
3. **Lesson not in RB-008:** before a known launch day, the Provisioning team must run a load test at 5 times normal Saturday volume and pre-scale consumers; the runbook should list the quarantine check as step 1, before looking at downstream systems.
4. Add a launch-calendar feed so Provisioning learns about device launches 14 days ahead.

## Linked runbook
RB-008 (SIM and eSIM Activation Provisioning Queue Stall)
