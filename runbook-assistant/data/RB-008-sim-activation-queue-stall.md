---
id: RB-008
title: SIM and eSIM Activation Provisioning Queue Stall
doc_type: runbook
service: SIM Activation
severity: SEV2
owner_team: Provisioning
last_updated: 2026-05-09
---

# RB-008: SIM and eSIM Activation Provisioning Queue Stall

## Symptoms
- Provisioning queue stalls: the oldest message in the `activation` queue is older than **8 minutes** (normal is under 90 seconds).
- Activation success rate in the retail app falls below 90% while the error text reads "activation pending".
- The `esim` lane shows consumers connected but zero acknowledgements for 5 minutes.
- Stores report that new SIMs inserted at the counter show a network name but no data session.

## Impact
New customers cannot start service. eSIM downloads complete but the profile never becomes active. Existing subscribers are not affected. Peak impact is Saturday morning when store activations are highest.

## Diagnosis steps
1. Check queue health: `provctl queue stats`. Compare `activation` and `esim` lanes.
2. Identify the stuck message: `provctl queue peek --lane esim --oldest`. A poison message that fails and retries endlessly blocks the lane head.
3. Check the downstream systems the activation touches in order: charging profile creation, HLR/HSS profile creation, then the eSIM subscription manager (SM-DP+). Use `provctl trace --id <MESSAGE_ID>` to see the last successful step.
4. If the HLR step fails, verify HSS health before touching the queue (see RB-001).

## Resolution steps
1. Move a poison message aside: `provctl queue quarantine --lane esim --id <MESSAGE_ID>`. The lane should resume within 1 minute.
2. If the lane is blocked by downstream slowness, drain with limited concurrency: `provctl queue drain --lane esim --concurrency 5`.
3. Replay quarantined messages after the fix with `provctl queue replay --lane esim --quarantine`. Replay in batches of at most 500.
4. Tell retail operations to continue selling; activations complete within 30 minutes once the queue clears.

## Escalation
- Provisioning on-call is paged when the oldest message passes 8 minutes.
- Escalate to Provisioning L2 if the queue is not draining **12 minutes** after the page.
- Escalate to the eSIM platform vendor and the Duty Manager at **50 minutes**.

## Related docs
- PM-006 (activation backlog postmortem)
- RB-001 (HLR/HSS profile creation failures)
- RB-007 (porting with new SIM)
