---
id: PM-005
title: Postmortem - Database Replication Lag Slowed CRM Lookups
doc_type: postmortem
service: CRM Care App
severity: SEV2
owner_team: Care Apps
last_updated: 2026-05-02
---

# PM-005: Database Replication Lag Slowed CRM Lookups

## Summary
On 14 April 2026 the read replica behind the CRM customer-profile service fell up to 11 minutes behind the primary. Agents saw outdated plan and balance data, and then repeated timeouts as the application retried reads. The contact centre estimated 22% longer handling time for about two hours.

## Timeline
- 09:40 A bulk plan-migration job starts on the primary database and writes 6 million rows.
- 09:55 Replica lag passes 60 seconds. No alert fires.
- 10:20 Agents report outdated data; the first ticket reaches Care Apps.
- 10:35 The CRM pool crosses 190 of 200 threads and the RB-004 alert fires.
- 10:50 On-call recycles the pool and scales to 6 nodes as the runbook says; it helps for ten minutes.
- 11:30 A database engineer identifies replication lag as the true cause.
- 11:45 The migration job is paused; the replica catches up by 12:05.

## Root cause
The bulk migration produced a write burst that the single-threaded replication apply process could not keep up with. The lag alert was configured on the replica **CPU** metric rather than on seconds behind primary, so it never fired. The application slowness looked like thread exhaustion, so the runbook for pool recycling was followed, which treated the symptom rather than the cause.

## What went well
- Scaling out reduced agent pain temporarily.
- Once identified, pausing the job restored service quickly.

## What did not go well
- Detection took 40 minutes.
- RB-004 contains no step to look at database replication state.

## Action items
1. Replace the lag alert with seconds-behind-primary: warn at 30 seconds, page at 120 seconds (owner: Database Services, due 2026-05-20).
2. Enable parallel replication apply with 8 workers on the CRM replica.
3. **Lesson not in the runbook:** bulk jobs touching more than 1 million rows must be announced via the change calendar and run in throttled batches of 50,000 rows with a 2-minute pause. Add a diagnosis step to RB-004: if threads are blocked on reads, check replica lag before recycling pools.

## Linked runbook
RB-004 (CRM and Customer-Care Application Unresponsive Under High Load); related symptoms in RB-006.
