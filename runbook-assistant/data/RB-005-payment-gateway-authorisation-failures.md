---
id: RB-005
title: Payment Gateway Authorisation Failures and Acquirer Timeouts
doc_type: runbook
service: Payment Gateway
severity: SEV1
owner_team: Payments Engineering
last_updated: 2026-01-30
---

# RB-005: Payment Gateway Authorisation Failures and Acquirer Timeouts

## Symptoms
- Card authorisation success rate drops below **96% over 5 minutes** (normal is 98.5%).
- Calls to the primary acquirer exceed a **3 second** response time or return `HTTP 504`.
- Top-up and bill-payment attempts fail with "payment could not be completed" in the app and web shop.
- The decline-code mix shifts toward code 91 (issuer unavailable) and code 96 (system malfunction).

## Impact
Customers cannot top up prepaid balances or pay bills. Prepaid customers with zero balance lose data service. Revenue loss is roughly proportional to the failure rate. Treat as SEV1 if success rate is below 90%.

## Diagnosis steps
1. Check the gateway dashboard "Auth Success by Acquirer" and compare the primary and secondary acquirers.
2. Run `paygwctl route show` to see which acquirer is receiving traffic and the current weights.
3. Run `paygwctl probe --acquirer primary`. If the probe latency is above 3 seconds, the problem is on the acquirer side or the network path to it.
4. Rule out our own side: check the gateway connection pool with `paygwctl pool show`. Exhaustion indicates a local issue rather than an acquirer issue.

## Resolution steps
1. If the primary acquirer is slow or failing: `paygwctl route set --acquirer secondary --weight 100`. Confirm success rate recovers within 5 minutes.
2. If the pool is exhausted: `paygwctl pool recycle` and then re-check the probe.
3. Enable the "retry once on 504" setting only on the secondary route: `paygwctl retry set --acquirer secondary --on 504 --max 1`.
4. Do not retry customer charges manually; duplicate charges are reconciled by Payments Reconciliation the next morning.

## Escalation
- Payments Engineering on-call is paged immediately on the success-rate alert.
- Escalate to the acquirer's technical bridge if the primary is still failing **10 minutes** after the page.
- Notify the Head of Digital Channels and the Duty Manager at **30 minutes**.

## Related docs
- PM-003 (acquirer timeout postmortem)
- RB-006 (API gateway 5xx, if the checkout API is also failing)
