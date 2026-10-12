---
id: PM-001
title: Postmortem - Attach Storm After Regional Power Event
doc_type: postmortem
service: HLR/HSS
severity: SEV1
owner_team: Core Signalling
last_updated: 2026-03-20
---

# PM-001: Attach Storm After Regional Power Event

## Summary
On 9 March 2026 a brief power event at the Northern regional site dropped about 410,000 handsets off the network. When power returned, all of them tried to re-attach within a few minutes. The HSS authentication queue saturated, the location-update reject rate peaked at 31%, and new attaches failed for 47 minutes. Registered subscribers outside the region were not affected.

## Timeline
- 02:14 Power event at Northern site; radio base stations restart.
- 02:19 Reject rate crosses 4.5% and Core Signalling is paged.
- 02:24 On-call restarts peer `s6a-peer-02`; no improvement as the AuC queue reached 6,300 entries.
- 02:34 Incident escalated to L2 (15-minute rule), who decide on failover.
- 02:41 Failover to HSS pod B started; the replica takes four minutes to warm.
- 02:52 Reject rate falls below 10%.
- 03:01 Reject rate below 1%. Incident downgraded.

## Root cause
The restart of the base stations produced a synchronised signalling surge far above the normal peak of attach requests. The HSS had no admission control, so the authentication queue grew until requests timed out and handsets retried immediately, which multiplied the load. The peer restart in the runbook did not help because the transport was healthy; the bottleneck was queue depth.

## What went well
- Alerting fired within five minutes of the event.
- The escalation timers were followed and L2 joined at the 15-minute mark.
- Failover to pod B worked as designed and no subscriber data was lost.

## What did not go well
- The on-call spent ten minutes on the peer restart before checking the AuC queue.
- Nobody knew whether the replica was current when failover was chosen.

## Action items
1. Add an admission-control rule that limits attach processing to 3,000 requests per second per HSS pod (owner: Core Signalling, due 2026-04-30).
2. Ask the radio team to stagger base-station restarts after power events by at least 30 seconds per cluster. This lesson is **not** in RB-001 and the runbook should say that a regional power or radio restart can cause a self-inflicted storm, so check the event log for a radio outage first.
3. Add a replica-lag figure to the failover command output.

## Linked runbook
RB-001 (HLR/HSS Subscriber Attach and Authentication Failures)
