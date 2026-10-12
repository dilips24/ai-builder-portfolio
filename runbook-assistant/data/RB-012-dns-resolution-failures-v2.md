---
id: RB-012
title: DNS Resolution Failures (Version 2, Current)
doc_type: runbook
service: DNS
severity: SEV2
owner_team: Network Services
last_updated: 2026-04-25
---

# RB-012: DNS Resolution Failures (Version 2, Current)

This runbook replaces RB-011, which described the retired resolver platform. It covers the anycast resolver service introduced in the autumn 2025 migration.

## Symptoms
- Resolver `SERVFAIL` rate above **1% over 5 minutes** on any anycast site.
- Applications log "temporary failure in name resolution" or intermittent connection timeouts to internal service names.
- Subscribers on mobile data report pages that load only after several retries, as the APN resolver answers slowly.
- Resolution latency (p95) above 250 ms at one site while the others are normal.

## Impact
Internal services and customer data sessions both rely on the resolvers. A failing anycast site can affect a regional share of subscribers, because queries are routed to the nearest site.

## Diagnosis steps
1. Identify the affected site: `dnsctl site status --all`. Compare SERVFAIL rate and p95 latency per site.
2. Test the resolver for a known internal name: `dnsctl query --view internal --name billing.nwm.internal`.
3. Check upstream forwarders: `dnsctl upstream health`. A dead forwarder shows as `UNREACHABLE` and causes SERVFAIL for external names only.
4. Check DNSSEC validation errors in the log; an expired signature on a signed zone will make that zone fail while others work.
5. Check certificate or key rollover changes in the last 24 hours.

## Resolution steps
1. If one site is bad, withdraw it from anycast: `dnsctl site withdraw --site <SITE>`. Traffic moves to the next nearest site within about 60 seconds.
2. Purge the cache for the internal view: `dnsctl cache purge --view internal`. During the incident, lower the TTL on affected records to **60 seconds** with `dnsctl ttl set --zone nwm.internal --ttl 60`; restore the normal 900 seconds afterwards.
3. If a forwarder is dead, remove it from rotation: `dnsctl upstream disable --name <FORWARDER>`.
4. For an expired DNSSEC signature, re-sign the zone with `dnsctl zone resign --zone <ZONE>` and wait for the signature refresh.
5. Re-advertise the site only after 10 minutes of clean metrics.

## Escalation
- Network Services on-call is paged automatically.
- Escalate to Network Services L2 if SERVFAIL stays above 1% **10 minutes** after the page.
- Escalate to the Head of Network Operations and the Duty Manager at **30 minutes**.

## Related docs
- RB-011 (superseded; do not use)
- RB-006 (gateway errors can follow resolver failures)
