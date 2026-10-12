---
id: RB-006
title: API Gateway Elevated 5xx Errors and Open Circuit Breakers
doc_type: runbook
service: API Gateway
severity: SEV2
owner_team: Platform Edge
last_updated: 2026-04-18
---

# RB-006: API Gateway Elevated 5xx Errors and Open Circuit Breakers

## Symptoms
- Gateway-level 5xx rate exceeds **2% over 3 minutes**.
- One or more upstream circuit breakers report state `OPEN`.
- Slow responses and timeouts under load across mobile app and partner APIs, with gateway nodes themselves at low CPU.
- Error responses carry `502` or `503` with the header `x-upstream-status: breaker-open`.

## Impact
Mobile app features that call backend services fail or show empty screens. Partner and reseller APIs return errors. The gateway is a shared entry point, so one failing backend can degrade several channels if breakers are mis-tuned.

## Diagnosis steps
1. List breakers: `gwctl breaker show`. Note which upstream services are `OPEN` or `HALF_OPEN`.
2. Check the failing upstream directly with `gwctl upstream probe --name <SERVICE>`. A failing probe means the backend, not the gateway, is the problem.
3. Check the backend database status for the service. Replication lag above 60 seconds on a read replica frequently makes read endpoints time out and trips the breaker.
4. Check whether the 5xx is concentrated on one region: `gwctl metrics --by region`.
5. Check certificates on the upstream mTLS connection: `gwctl cert list --expiring 14d`.

## Resolution steps
1. If the problem is isolated to one region or one backend pool, shift traffic: `gwctl upstream failover --service <SERVICE> --to eu-west-b`.
2. Do not manually close a breaker while the probe still fails; it will reopen and extend the outage. Close only after the probe passes 3 times: `gwctl breaker reset --name <SERVICE>`.
3. If a backend is overloaded, enable load shedding for low-priority partners: `gwctl shed enable --tier bronze`.
4. If a certificate has expired, replace it with `gwctl cert rotate --name <NAME>` using the approved certificate from the secrets vault.

## Escalation
- Platform Edge on-call is paged automatically.
- Escalate to Platform Edge L2 if 5xx stays above 2% **15 minutes** after the page.
- Escalate to the owning backend team and the Duty Manager at **35 minutes**.

## Related docs
- PM-004 (certificate expiry causing gateway errors)
- RB-004 (CRM thread-pool exhaustion: similar slow symptoms, different cause)
