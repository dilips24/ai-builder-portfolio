---
id: RB-004
title: CRM and Customer-Care Application Unresponsive Under High Load
doc_type: runbook
service: CRM Care App
severity: SEV2
owner_team: Care Apps
last_updated: 2026-03-27
---

# RB-004: CRM and Customer-Care Application Unresponsive Under High Load

## Symptoms
- Application unresponsive under high load: agent search and account-view requests take longer than 15 seconds and then time out.
- Active request threads on the `agent-ui` pool stay above **190 of 200** for more than 5 minutes.
- CPU on the application nodes is low (under 40%) while the request queue grows.
- Health check endpoint `/health/deep` returns slowly or intermittently fails.

## Impact
Care agents in the contact centre cannot look up accounts or handle calls efficiently. Average handle time rises and the call queue builds. Self-care web and mobile app are served by a different pool and normally stay up.

## Diagnosis steps
1. Check pool saturation: `crmadm pool show --pool agent-ui`. Note active, queued and blocked thread counts.
2. Take a thread dump: `crmadm thread-dump --node <NODE>` and look for many threads waiting on the same downstream call (typically the customer-profile service or an address validation lookup).
3. Check node CPU. Low CPU together with full pools indicates threads blocked on I/O, not a compute problem.
4. Compare with the start of the morning shift: login storms at 08:00 and 13:00 shift change regularly push the pool to its limit.

## Resolution steps
1. Recycle the pool one node at a time: `crmadm pool recycle --pool agent-ui --node <NODE> --drain`. Wait for in-flight requests to finish (up to 90 seconds) before the next node.
2. Scale the tier from 4 to **6 nodes** with `crmadm scale --tier app --replicas 6`. Scale-out takes about 4 minutes.
3. If a single downstream call is the common blocker, disable the optional address-validation lookup with the feature flag `crm.addr_validate=off`.
4. After recovery, lower the agent-ui thread timeout back to the default of 12 seconds if it was changed.

## Escalation
- Care Apps on-call is paged automatically at the pool threshold.
- Escalate to Care Apps L2 if agents still cannot work **20 minutes** after the page.
- Escalate to the vendor support desk at **45 minutes**.

## Related docs
- PM-005 (replication lag affected CRM lookups)
- RB-006 (similar slow-response symptoms at the API gateway, different cause and fix)
