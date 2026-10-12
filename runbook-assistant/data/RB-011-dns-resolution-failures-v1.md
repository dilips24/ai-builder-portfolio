---
id: RB-011
title: DNS Resolution Failures (Version 1)
doc_type: runbook
service: DNS
severity: SEV2
owner_team: Network Services
last_updated: 2025-06-10
---

# RB-011: DNS Resolution Failures (Version 1)

> **SUPERSEDED by RB-012.** Do not use this document during incidents. The commands and timers below reflect the old resolver platform, which was decommissioned in the autumn 2025 migration. It is kept for audit history only.

## Symptoms
- Internal applications log "name not found" for hostnames that exist.
- Resolver error rate above 3% for 10 minutes.
- Mobile data users see "no internet" while connected, because the default APN resolver is failing.

## Impact
Applications that depend on service names fail. Customers on data sessions cannot load websites if the APN resolvers are affected.

## Diagnosis steps
1. Query the primary resolver directly: `dig @10.20.0.10 example.nwm.internal`.
2. Check the resolver process with `dnsctl status --node ns1`.
3. Look at the cache hit ratio; below 60% suggests a cache problem.
4. Check zone transfer status between `ns1` and `ns2` with `dnsctl axfr-status`. A serial number mismatch means the secondary is serving stale records.
5. Review recent changes to the internal zone file; a syntax error in a zone causes that zone to be dropped while others keep answering.

## Resolution steps
1. Flush the zone cache: `dnsctl flush --zone nwm.internal`. Records are cached with a default TTL of **300 seconds**, so wait 5 minutes for clients to refresh.
2. Restart the resolver service on `ns1` and then `ns2` with `dnsctl restart --node ns1`.
3. If the problem continues, switch clients to the secondary resolver pair by editing the DHCP option and waiting for lease renewal (up to 30 minutes).

4. After recovery, confirm the error rate is below 0.5% for 15 minutes and record the serial numbers of both resolvers in the incident log.

## Escalation
- Network Services on-call is paged by phone.
- Escalate to Network Services L2 after **30 minutes**.
- Escalate to the Duty Manager after **2 hours**.

## Related docs
- RB-012 (current version; use this instead)
