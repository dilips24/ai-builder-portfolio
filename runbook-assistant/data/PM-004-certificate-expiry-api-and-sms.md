---
id: PM-004
title: Postmortem - Expired Intermediate Certificate Broke API and SMS Traffic
doc_type: postmortem
service: API Gateway
severity: SEV1
owner_team: Platform Edge
last_updated: 2026-04-08
---

# PM-004: Expired Intermediate Certificate Broke API and SMS Traffic

## Summary
On 28 March 2026 at 00:00 UTC an intermediate certificate in the chain used for mutual TLS between the API gateway and the SMS aggregator and several partner APIs expired. The leaf certificates were valid for another seven months, so no expiry alert fired. Partner API calls failed with TLS handshake errors and outbound SMS through the primary aggregator stopped for 1 hour 34 minutes.

## Timeline
- 00:00 Intermediate certificate expires.
- 00:06 Gateway 5xx rate crosses 2%; Platform Edge paged. At the same time the SMS queue depth passes 50,000 and Messaging Platform is paged.
- 00:20 Two teams investigate in parallel; Messaging Platform suspects the aggregator, Platform Edge suspects an upstream breaker.
- 00:41 A engineer notices `x509: certificate has expired` in the TLS logs of the gateway.
- 01:10 New intermediate chain obtained from the certificate authority and loaded with `gwctl cert rotate`.
- 01:34 SMS traffic fully drained; incident closed.

## Root cause
Certificate monitoring checked only leaf certificates and their expiry dates. The intermediate in the chain expired earlier than the leaf, which no inventory or alert covered. Chain details were not in the certificate register, and the expiry date was nine months earlier than the leaf's date.

## What went well
- Both on-call teams were paged automatically and later joined one bridge.
- The new chain was available from the certificate authority within 30 minutes.

## What did not go well
- Parallel investigation wasted 35 minutes because there was no shared incident channel.
- The runbook was used by only one of the two teams.

## Action items
1. Add the full chain (leaf, intermediates, root) to the certificate register and alert at 30 days, 14 days and 3 days before the earliest expiry (owner: Platform Edge, due 2026-05-15).
2. **Lesson not in RB-006:** the runbook lists `gwctl cert list --expiring 14d`, but this command only shows leaf certificates. Add `gwctl cert chain --check` as a diagnosis step.
3. Create a shared bridge rule: when two services alarm within 10 minutes with errors involving TLS, open one joint incident.

## Linked runbook
RB-006 (API Gateway Elevated 5xx Errors and Open Circuit Breakers); see also RB-003 for SMS queue handling.
