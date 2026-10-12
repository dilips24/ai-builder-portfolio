---
id: RB-001
title: HLR/HSS Subscriber Attach and Authentication Failures
doc_type: runbook
service: HLR/HSS
severity: SEV1
owner_team: Core Signalling
last_updated: 2026-03-14
---

# RB-001: HLR/HSS Subscriber Attach and Authentication Failures

## Symptoms
- Location-update reject rate on the S6a/MAP interfaces exceeds **4.5% for 10 consecutive minutes**.
- Authentication-vector requests time out; the AuC request queue depth rises above 2,000 entries.
- Diameter peer `s6a-peer-02` flaps between OPEN and CLOSED in the signalling dashboard.
- Handsets in the affected area show "emergency calls only" after reboot, while already-registered subscribers keep service.

## Impact
New attaches and re-registrations fail. Subscribers who power-cycle their handset or travel between tracking areas lose data and voice. Roaming-in subscribers are affected the same way. Treat as SEV1 when more than 50,000 subscribers are affected.

## Diagnosis steps
1. Open the "Signalling Health" dashboard and note the reject cause split (unknown subscriber vs. authentication failure vs. system failure).
2. Check one affected subscriber: `hlrctl show subscriber --imsi <IMSI>`. Confirm the profile exists and the state is `ACTIVE`.
3. Check the Diameter peer: `hsscfg peer-status --name s6a-peer-02`. A state other than `OPEN` points at the transport.
4. Check AuC queue depth: `hlrctl auc queue`. Above 2,000 means the AuC is saturated rather than the network path being down.
5. Check the last 30 minutes of change records for provisioning bulk loads, which can lock the subscriber database.

## Resolution steps
1. If only the peer is unhealthy: `hsscfg restart-peer --name s6a-peer-02`. Wait 2 minutes and re-check the reject rate.
2. If AuC queue depth stays above 2,000 after 5 minutes: fail over to HSS pod B with `hsscfg failover --target pod-b`. Pod B holds a replica that is at most 90 seconds behind.
3. If a bulk provisioning load is running, pause it with `provctl job pause --name bulk-import` before restarting anything.
4. After recovery, keep the incident open for 30 minutes and watch the reject rate stay below 1%.

## Escalation
- Core Signalling on-call is paged automatically.
- Escalate to Core Signalling L2 if the reject rate is still above 4.5% **15 minutes** after the incident opens.
- Escalate to the Core Network L3 vendor engineer at **40 minutes**.
- Notify the Duty Manager at SEV1 declaration.

## Related docs
- PM-001 (attach storm postmortem)
- RB-009 (roaming attach problems at partner networks)
- RB-008 (SIM activation, if new profiles are missing)
