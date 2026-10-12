---
id: PM-003
title: Postmortem - Payment Authorisation Failures During Acquirer Degradation
doc_type: postmortem
service: Payment Gateway
severity: SEV1
owner_team: Payments Engineering
last_updated: 2026-02-18
---

# PM-003: Payment Authorisation Failures During Acquirer Degradation

## Summary
On 6 February 2026, between 18:05 and 18:52, card authorisation success dropped to a low of 71% after the primary acquirer began responding in 4–9 seconds. Around 38,000 top-up attempts failed. The incident ended after traffic was moved to the secondary acquirer.

## Timeline
- 18:05 Primary acquirer latency rises; success rate falls to 93%.
- 18:08 Alert fires (success rate below 96% over 5 minutes) and Payments Engineering is paged.
- 18:13 On-call confirms the probe latency is above 3 seconds.
- 18:20 Decision to route to the secondary, but the secondary had a weight of 0 and a stale credential.
- 18:31 Credential refreshed by hand; weight set to 100.
- 18:36 Success rate recovers above 96%.
- 18:52 Primary acquirer reports its issue resolved; traffic stays on secondary until the next morning.

## Root cause
The primary acquirer suffered a database failover on their side. Our gateway waited the full 10-second default timeout per attempt, which tied up connections and caused local pool exhaustion, extending the impact. The secondary route had never been exercised in production for four months, and its API credential had been rotated without the gateway being updated.

## What went well
- The alert fired in three minutes.
- The acquirer's technical bridge was joined within the 10-minute limit.
- No duplicate charges were created because manual retries were avoided.

## What did not go well
- The secondary route was untested and unusable for 23 minutes.
- Escalation to the Duty Manager happened at the 30-minute mark only after a manager asked for an update.

## Action items
1. Reduce the acquirer call timeout from 10 seconds to 4 seconds (owner: Payments Engineering, due 2026-02-27).
2. Run a weekly synthetic transaction against the secondary acquirer and alert if it fails. This is **not** covered by RB-005, which assumes the secondary is healthy.
3. Add credential rotation of acquirer keys to the secrets checklist so the gateway is updated in the same change.

## Linked runbook
RB-005 (Payment Gateway Authorisation Failures and Acquirer Timeouts)
